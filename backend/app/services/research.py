"""LangGraph pipeline. Every inference is routed through the audited LLM provider."""

import hashlib
import re
import time
from datetime import UTC, datetime
from itertools import combinations
from typing import Any, TypedDict

from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

try:
    from langgraph.graph import END, START, StateGraph
except (
    ImportError
):  # only makes local import diagnostics possible when optional native dependencies are blocked
    raise RuntimeError("LangGraph must be installed to run Atlas research workflows")

from app.config import settings
from app.domain.models import (
    ClaimComparison,
    Entity,
    EntityMention,
    EntityRelationship,
    EvidenceChunk,
    Finding,
    ResearchSession,
    RunEvent,
    SessionSourceLink,
    Source,
)
from app.services.providers import (
    LlmContext,
    llm_chat,
    llm_json,
    qdrant_search,
    qdrant_upsert,
    source_profile,
    tavily_search,
)


class ResearchState(TypedDict, total=False):
    session_id: str
    question: str
    request_id: str
    subquestions: list[str]
    candidates: list[dict[str, Any]]
    source_ids: list[str]
    reused_source_ids: list[str]
    finding_ids: list[str]
    contradiction_count: int


def event(
    db: Session, session_id: str, step: str, status: str, began: float, **details: Any
) -> None:
    try:
        db.add(
            RunEvent(
                id=str(uuid4()),
                research_session_id=session_id,
                step=step,
                status=status,
                duration_ms=round((time.perf_counter() - began) * 1000, 1),
                details=details,
            )
        )
        db.commit()
    except Exception:
        db.rollback()


def context(db: Session, state: ResearchState, node: str) -> LlmContext:
    return LlmContext(db, state["session_id"], node, state["request_id"])


def abstract(index: dict[str, list[int]] | None) -> str:
    if not index:
        return "No abstract"
    positions = [i for values in index.values() for i in values]
    if not positions:
        return "No abstract"
    words = ["" for _ in range(max(positions) + 1)]
    for word, pos_list in index.items():
        for position in pos_list:
            words[position] = word
    return " ".join(words)


def chunks(text: str, size: int = 1200, overlap: int = 180) -> list[tuple[int, int, str]]:
    values, start = [], 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = max(text.rfind(". ", start, end), text.rfind("\n", start, end))
            end = boundary + 1 if boundary > start + size // 2 else end
        value = text[start:end].strip()
        if value:
            offset = text.find(value, start, end)
            values.append((offset, offset + len(value), value))
        start = max(end - overlap, start + 1)
    return values


def plan_node(db: Session, state: ResearchState) -> ResearchState:
    began = time.perf_counter()
    payload = llm_json(
        "Decompose an enterprise research question into complementary searchable questions.",
        f'Question: {state["question"]}\nSchema: {{"subquestions":["..."]}}. Return 3-5.',
        context(db, state, "plan"),
    )
    if not isinstance(payload, dict) or not isinstance(payload.get("subquestions"), list):
        raise ValueError("Planner returned no subquestions")
    subquestions = [
        str(value).strip() for value in payload["subquestions"] if len(str(value).strip()) >= 8
    ][:5]
    if not subquestions:
        raise ValueError("Planner returned no usable subquestions")
    event(db, state["session_id"], "plan", "completed", began, subquestions=subquestions)
    return {"subquestions": subquestions}


def _reuse_sources(db: Session, state: ResearchState, subquestion: str) -> list[str]:
    hits = qdrant_search(subquestion, limit=12, context=context(db, state, "retrieve"))
    source_ids = list(
        dict.fromkeys(
            str(hit.get("payload", {}).get("source_id"))
            for hit in hits
            if float(hit.get("score", 0)) >= settings().atlas_reuse_threshold
        )
    )
    valid = [source_id for source_id in source_ids if db.get(Source, source_id)]
    for source_id in valid:
        if not db.scalar(
            select(SessionSourceLink).where(
                SessionSourceLink.research_session_id == state["session_id"],
                SessionSourceLink.source_id == source_id,
            )
        ):
            db.add(
                SessionSourceLink(
                    research_session_id=state["session_id"], source_id=source_id, origin="reused"
                )
            )
    db.commit()
    return valid


def _fetch_subquestion_web_and_academic(subquestion: str) -> tuple[str, list[dict[str, Any]], int]:
    candidates, fetched = [], 0
    web_results = tavily_search(subquestion, 3)
    for item in web_results:
        if item.get("url") and item.get("content"):
            item.update(query=subquestion, origin=item.get("origin", "web_search"))
            candidates.append(item)
            fetched += 1

    try:
        clean_query = re.sub(r'[^\w\s]', ' ', subquestion).strip()
        response = httpx.get(
            settings().openalex_url, params={"search": clean_query, "per-page": 2}, timeout=3
        )
        if response.status_code == 200:
            for work in response.json().get("results", []):
                text = abstract(work.get("abstract_inverted_index"))
                if text and text != "No abstract":
                    candidates.append(
                        {
                            "title": work.get("title", "Academic source"),
                            "url": work.get("doi") or work.get("id", ""),
                            "content": text,
                            "score": 0.8,
                            "published_date": work.get("publication_date"),
                            "query": subquestion,
                            "origin": "openalex",
                        }
                    )
                    fetched += 1
    except Exception:
        pass
    return subquestion, candidates, fetched


def retrieve_node(db: Session, state: ResearchState) -> ResearchState:
    began, candidates, reused = time.perf_counter(), [], []
    subquestions = state.get("subquestions", [])[:3]

    for sq in subquestions:
        known = _reuse_sources(db, state, sq)
        reused.extend(known)

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_fetch_subquestion_web_and_academic, sq): sq for sq in subquestions
        }
        for future in as_completed(futures):
            try:
                sq, sq_candidates, fetched = future.result()
                candidates.extend(sq_candidates)
                event(
                    db,
                    state["session_id"],
                    "reuse_and_retrieve",
                    "completed",
                    began,
                    query=sq,
                    reused_chunks=0,
                    reused_sources=0,
                    fetched_sources=fetched,
                )
            except Exception:
                pass

    unique = {
        hashlib.sha256((item["url"] + item["content"][:1000]).encode()).hexdigest(): item
        for item in candidates
    }
    event(
        db,
        state["session_id"],
        "retrieve",
        "completed",
        began,
        records=len(unique),
        reused_sources=len(set(reused)),
    )
    return {"candidates": list(unique.values()), "reused_source_ids": list(dict.fromkeys(reused))}


def store_node(db: Session, state: ResearchState) -> ResearchState:
    began, source_ids = time.perf_counter(), list(state.get("reused_source_ids", []))
    for item in state.get("candidates", []):
        content = item["content"].strip()[:30000]
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        source = db.scalar(select(Source).where(Source.content_hash == content_hash))
        origin = "reused" if source else "fetched"
        if not source:
            source_type, primary, baseline = source_profile(item["url"], item["title"])
            source = Source(
                research_session_id=state["session_id"],
                first_seen_session_id=state["session_id"],
                title=item["title"],
                url=item["url"],
                canonical_url=item["url"],
                content_hash=content_hash,
                publisher=item["origin"],
                published_at=item.get("published_date"),
                abstract=content,
                source_type="academic_research" if item["origin"] == "openalex" else source_type,
                is_primary=True if item["origin"] == "openalex" else primary,
                reliability_score=round((baseline + item["score"]) / 2, 2),
            )
            db.add(source)
            db.commit()
            db.refresh(source)
            for ordinal, (start, end, text) in enumerate(chunks(content)):
                db.add(
                    EvidenceChunk(
                        source_id=source.id,
                        ordinal=ordinal,
                        text=text,
                        char_start=start,
                        char_end=end,
                        content_hash=hashlib.sha256(text.encode()).hexdigest(),
                    )
                )
                qdrant_upsert(
                    f"{source.id}-{ordinal}",
                    text,
                    {"source_id": source.id, "chunk": ordinal},
                    context(db, state, "store"),
                )
            db.commit()
        if not db.scalar(
            select(SessionSourceLink).where(
                SessionSourceLink.research_session_id == state["session_id"],
                SessionSourceLink.source_id == source.id,
            )
        ):
            db.add(
                SessionSourceLink(
                    research_session_id=state["session_id"], source_id=source.id, origin=origin
                )
            )
            db.commit()
        source_ids.append(source.id)
    event(
        db, state["session_id"], "store_and_index", "completed", began, sources=len(set(source_ids))
    )
    return {"source_ids": list(dict.fromkeys(source_ids))}


def extract_node(db: Session, state: ResearchState) -> ResearchState:
    began, ids = time.perf_counter(), []
    for source_id in state.get("source_ids", []):
        source = db.get(Source, source_id)
        if not source or not source.abstract:
            continue
        old = list(
            db.scalars(
                select(Finding).where(
                    Finding.source_id == source.id,
                    Finding.research_session_id != state["session_id"],
                )
            )
        )
        if source_id in state.get("reused_source_ids", []) and old:
            claims = [
                {
                    "claim": f.claim,
                    "quote": f.evidence_span,
                    "topic": f.topic_key,
                    "classification": f.classification,
                    "confidence": f.confidence,
                }
                for f in old[:4]
            ]
        else:
            payload = llm_json(
                "Extract verifiable atomic claims. Every quote must be an exact substring of the source.",
                f'Source text:\n{source.abstract[:7000]}\nSchema: {{"claims":[{{"claim":"paraphrase","quote":"exact quote","topic":"normalized topic","classification":"technology|outcome|risk|adoption|governance"}}]}}',
                context(db, state, "extract"),
            )
            if not isinstance(payload, dict) or not isinstance(payload.get("claims"), list):
                raise ValueError("Claim extractor returned invalid schema")
            claims = payload["claims"]
        for item in claims[:4]:
            quote = str(item.get("quote", "")).strip()
            start = source.abstract.find(quote)
            if start < 0 or len(quote) < 20:
                continue
            finding = Finding(
                research_session_id=state["session_id"],
                source_id=source.id,
                claim=str(item.get("claim", quote)).strip(),
                evidence_span=quote,
                evidence_start=start,
                evidence_end=start + len(quote),
                confidence=float(item.get("confidence", source.reliability_score)),
                classification=str(item.get("classification", "evidence"))[:64],
                topic_key=str(item.get("topic", "research finding")).strip().lower()[:160]
                or "research finding",
            )
            db.add(finding)
            db.commit()
            ids.append(finding.id)
    event(
        db,
        state["session_id"],
        "extract_claims",
        "completed",
        began,
        findings=len(ids),
        exact_quote_offsets=True,
    )
    return {"finding_ids": ids}


def entities_node(db: Session, state: ResearchState) -> ResearchState:
    began = time.perf_counter()
    mentions = 0
    findings = list(
        db.scalars(select(Finding).where(Finding.research_session_id == state["session_id"]))
    )
    for finding in findings:
        payload = llm_json(
            "Extract named entities that occur verbatim in the quoted evidence. Do not infer entities.",
            f'Evidence: {finding.evidence_span}\nSchema: {{"entities":[{{"name":"exact mention","type":"org|person|technology|product|regulation|location|other"}}]}}',
            context(db, state, "entities"),
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("entities"), list):
            raise ValueError("Entity extractor returned invalid schema")
        entities = []
        for item in payload["entities"]:
            name = str(item.get("name", "")).strip()
            offset = finding.evidence_span.find(name)
            if offset < 0 or not name:
                continue
            key = re.sub(r"\W+", "", name.lower())
            entity = db.scalar(select(Entity).where(Entity.canonical_key == key))
            if not entity:
                entity = Entity(
                    research_session_id=state["session_id"],
                    first_seen_research_session_id=state["session_id"],
                    name=name,
                    canonical_key=key,
                    entity_type=str(item.get("type", "other"))[:64],
                    confidence=finding.confidence,
                )
                db.add(entity)
                db.commit()
                db.refresh(entity)
            db.add(
                EntityMention(
                    entity_id=entity.id,
                    finding_id=finding.id,
                    source_id=finding.source_id,
                    research_session_id=state["session_id"],
                    mention_text=name,
                    char_start=offset,
                    char_end=offset + len(name),
                )
            )
            db.commit()
            entities.append(entity)
            mentions += 1
        for a, b in combinations(entities, 2):
            db.add(
                EntityRelationship(
                    research_session_id=state["session_id"],
                    source_entity_id=a.id,
                    target_entity_id=b.id,
                    entity_a_id=a.id,
                    entity_b_id=b.id,
                    relation_type="co_occurs",
                    relationship_type="co_occurs",
                    evidence_finding_id=finding.id,
                    confidence=finding.confidence,
                    explanation="Entities co-occur in the cited finding.",
                )
            )
    db.commit()
    event(db, state["session_id"], "entities", "completed", began, mentions=mentions)
    return {}


def compare_node(db: Session, state: ResearchState) -> ResearchState:
    began = time.perf_counter()
    findings = list(
        db.scalars(select(Finding).where(Finding.research_session_id == state["session_id"]))
    )
    contradictions = 0
    for a, b in combinations(findings, 2):
        if a.topic_key != b.topic_key or a.source_id == b.source_id:
            continue
        payload = llm_json(
            "Compare two evidence-backed claims only from supplied text.",
            f'A: {a.claim}\nB: {b.claim}\nSchema: {{"relationship":"support|contradict|unclear","explanation":"why","confidence":0.0}}',
            context(db, state, "compare"),
        )
        if not isinstance(payload, dict) or payload.get("relationship") not in {
            "support",
            "contradict",
            "unclear",
        }:
            raise ValueError("Comparator returned invalid relationship")
        relationship = payload["relationship"]
        confidence = max(0, min(1, float(payload.get("confidence", 0.5))))
        db.add(
            ClaimComparison(
                research_session_id=state["session_id"],
                finding_a_id=a.id,
                finding_b_id=b.id,
                relationship=relationship,
                explanation=str(payload.get("explanation", ""))[:1000],
                confidence=confidence,
            )
        )
        if relationship == "contradict":
            a.stance = b.stance = "contradicted"
            contradictions += 1
    db.commit()
    event(
        db,
        state["session_id"],
        "compare_evidence",
        "completed",
        began,
        contradictions=contradictions,
    )
    return {"contradiction_count": contradictions}


def synthesize_node(db: Session, state: ResearchState) -> ResearchState:
    began = time.perf_counter()
    research = db.get(ResearchSession, state["session_id"])
    findings = list(
        db.scalars(
            select(Finding)
            .where(Finding.research_session_id == state["session_id"])
            .order_by(Finding.confidence.desc())
        )
    )
    if not findings:
        raise ValueError("No verified findings were available for synthesis")

    source_map = {}
    for item in findings:
        if item.source_id and item.source_id not in source_map:
            s = db.get(Source, item.source_id)
            if s:
                source_map[item.source_id] = s

    evidence_lines = []
    for item in findings[:8]:
        evidence_lines.append(f"- {item.claim}")

    evidence = "\n".join(evidence_lines)

    system_prompt = (
        "You are an expert AI research assistant. Answer the user's question directly, fluently, and concisely. "
        "Do NOT include any URLs, HTTP links, bracketed source links, or raw paper citations in the answer text section. "
        "Structure your response cleanly into two parts:\n"
        "### Overview & Explanation\n(Provide a clear, well-written overview explaining the topic directly in response to the user's question)\n\n"
        "### Key Points\n(Provide a concise bulleted list of the core takeaways and actionable insights)."
    )
    user_prompt = (
        f"Question: {state['question']}\n"
        f"Verified Research Findings:\n{evidence}"
    )

    research.conclusion = llm_chat(
        system_prompt,
        user_prompt,
        context(db, state, "synthesize"),
    )
    base = sum(x.confidence for x in findings) / len(findings)
    research.confidence = round(max(0, base - state.get("contradiction_count", 0) * 0.04), 2)
    research.status = "completed"
    research.completed_at = datetime.now(UTC)
    db.commit()
    event(db, state["session_id"], "synthesize", "completed", began, confidence=research.confidence)
    return {}


def build_research_graph(db: Session):
    graph = StateGraph(ResearchState)
    for name, node in {
        "plan": plan_node,
        "retrieve": retrieve_node,
        "store": store_node,
        "extract": extract_node,
        "entities": entities_node,
        "compare": compare_node,
        "synthesize": synthesize_node,
    }.items():
        graph.add_node(name, lambda state, node=node: node(db, state))
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "store")
    graph.add_edge("store", "extract")
    graph.add_edge("extract", "entities")
    graph.add_edge("entities", "compare")
    graph.add_edge("compare", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


def run_research(db: Session, question: str, session_id: str | None = None) -> ResearchSession:
    research = db.get(ResearchSession, session_id) if session_id else None
    if not research:
        research = ResearchSession(question=question, status="running")
        db.add(research)
        db.commit()
        db.refresh(research)
    try:
        build_research_graph(db).invoke(
            {"session_id": research.id, "question": question, "request_id": research.id}
        )
    except Exception as exc:
        research.status = "failed"
        research.completed_at = datetime.now(UTC)
        research.conclusion = None
        db.commit()
        event(db, research.id, "workflow", "failed", time.perf_counter(), error=str(exc))
    db.refresh(research)
    return research
