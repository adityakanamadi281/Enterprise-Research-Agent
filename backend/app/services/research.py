import time
from datetime import UTC, datetime
import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.config import settings
from app.domain.models import Entity, EntityRelationship, Finding, ResearchSession, RunEvent, Source
from app.services.providers import (
    cache_key,
    fireworks_chat,
    provider_status,
    qdrant_upsert,
    redis_get,
    redis_set,
    tavily_search,
)


def event(db, id, step, status, began, **details):
    db.add(
        RunEvent(
            research_session_id=id,
            step=step,
            status=status,
            duration_ms=round((time.perf_counter() - began) * 1000, 1),
            details=details,
        )
    )
    db.commit()


def abstract(index):
    if not index:
        return "No abstract supplied by this provider."
    words = ["" for _ in range(max(i for ps in index.values() for i in ps) + 1)]
    for word, ps in index.items():
        for p in ps:
            words[p] = word
    return " ".join(words)


def run_research(db: Session, question: str):
    research = ResearchSession(question=question, status="running")
    db.add(research)
    db.commit()
    db.refresh(research)
    providers = provider_status()
    began = time.perf_counter()
    plan = [question]
    if providers["fireworks"]:
        try:
            planned = fireworks_chat(
                "You are an enterprise research planner. Return three concise search queries, one per line.",
                question,
            )
            plan = [
                line.removeprefix("- ").strip()
                for line in (planned or "").splitlines()
                if line.strip()
            ][:3] or plan
        except httpx.HTTPError as exc:
            event(db, research.id, "plan", "degraded", began, provider="fireworks", error=str(exc))
    event(
        db,
        research.id,
        "plan",
        "completed",
        began,
        subquestions=plan,
        provider="fireworks" if providers["fireworks"] else "deterministic_fallback",
    )
    topic = Entity(
        research_session_id=research.id,
        name=question,
        entity_type="research_question",
        confidence=1,
    )
    db.add(topic)
    db.commit()
    began = time.perf_counter()
    cache_id = cache_key("openalex", question.lower().strip())
    try:
        works = redis_get(cache_id)
        cache_hit = works is not None
        if works is None:
            params = {"search": question, "per-page": 6}
            if settings().openalex_api_key:
                params["api_key"] = settings().openalex_api_key
            r = httpx.get(settings().openalex_url, params=params, timeout=12)
            r.raise_for_status()
            works = r.json().get("results", [])
            redis_set(cache_id, works)
        event(
            db,
            research.id,
            "retrieve",
            "completed",
            began,
            provider=settings().research_provider,
            records=len(works),
            cache="hit" if cache_hit else "miss",
            cache_provider="upstash_redis" if providers["upstash_redis"] else "disabled",
        )
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        works = []
        event(
            db,
            research.id,
            "retrieve",
            "degraded",
            began,
            provider=settings().research_provider,
            error=str(exc),
        )
    web_started = time.perf_counter()
    try:
        web_results = tavily_search(question)
        event(
            db,
            research.id,
            "web_search",
            "completed" if providers["tavily"] else "skipped",
            web_started,
            provider="tavily",
            records=len(web_results),
        )
    except httpx.HTTPError as exc:
        web_results = []
        event(
            db,
            research.id,
            "web_search",
            "degraded",
            web_started,
            provider="tavily",
            error=str(exc),
        )
    began = time.perf_counter()
    for work in works:
        text = abstract(work.get("abstract_inverted_index"))
        score = min(
            0.95,
            0.45 + min(work.get("cited_by_count", 0), 300) / 600 + (0.12 if work.get("doi") else 0),
        )
        source = Source(
            research_session_id=research.id,
            title=work.get("title", "Untitled source"),
            url=work.get("doi") or work.get("id"),
            publisher=((work.get("primary_location") or {}).get("source") or {}).get(
                "display_name"
            ),
            published_at=work.get("publication_date"),
            abstract=text,
            reliability_score=score,
        )
        db.add(source)
        db.commit()
        try:
            indexed = qdrant_upsert(
                source.id,
                f"{source.title}\n{text}",
                {"research_session_id": research.id, "source_id": source.id, "title": source.title},
            )
            if indexed:
                event(
                    db,
                    research.id,
                    "index_evidence",
                    "completed",
                    time.perf_counter(),
                    provider="qdrant",
                )
        except httpx.HTTPError as exc:
            event(
                db,
                research.id,
                "index_evidence",
                "degraded",
                time.perf_counter(),
                provider="qdrant",
                error=str(exc),
            )
        db.refresh(source)
        source_entity = Entity(
            research_session_id=research.id,
            name=source.title,
            entity_type="evidence_source",
            confidence=source.reliability_score,
        )
        db.add(source_entity)
        db.commit()
        db.add(
            EntityRelationship(
                research_session_id=research.id,
                source_entity_id=topic.id,
                target_entity_id=source_entity.id,
                relation_type="supported_by",
                confidence=source.reliability_score,
            )
        )
        db.commit()
        if text != "No abstract supplied by this provider.":
            db.add(
                Finding(
                    research_session_id=research.id,
                    source_id=source.id,
                    claim=source.title,
                    evidence_span=text[:800],
                    confidence=score,
                    classification="peer_reviewed_research",
                )
            )
            db.commit()
    for result in web_results:
        text = result["content"][:8000]
        if not text or not result["url"]:
            continue
        source = Source(
            research_session_id=research.id,
            title=result["title"],
            url=result["url"],
            publisher="tavily_web_search",
            abstract=text,
            reliability_score=max(0.3, min(0.9, result["score"])),
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        db.add(
            Finding(
                research_session_id=research.id,
                source_id=source.id,
                claim=source.title,
                evidence_span=text[:800],
                confidence=source.reliability_score,
                classification="web_research",
            )
        )
        db.commit()
        try:
            qdrant_upsert(
                source.id,
                f"{source.title}\n{text}",
                {"research_session_id": research.id, "source_id": source.id, "kind": "web"},
            )
        except httpx.HTTPError:
            pass
    count = db.scalar(
        select(func.count(Finding.id)).where(Finding.research_session_id == research.id)
    )
    event(db, research.id, "extract_evidence", "completed", began, findings=count)
    began = time.perf_counter()
    findings = list(
        db.scalars(
            select(Finding)
            .where(Finding.research_session_id == research.id)
            .order_by(Finding.confidence.desc())
        )
    )
    research.conclusion = None
    if findings and providers["fireworks"]:
        try:
            evidence = "\n".join(f"- {f.claim}: {f.evidence_span[:350]}" for f in findings[:5])
            research.conclusion = fireworks_chat(
                "Synthesize an executive answer using only supplied evidence. State uncertainty when evidence is limited. Keep it under 140 words.",
                f"Question: {question}\nEvidence:\n{evidence}",
            )
        except httpx.HTTPError as exc:
            event(
                db,
                research.id,
                "synthesize",
                "degraded",
                began,
                provider="fireworks",
                error=str(exc),
            )
    research.conclusion = research.conclusion or (
        ("Evidence-backed starting point: " + " ".join(f.claim for f in findings[:3]))
        if findings
        else "No retrievable evidence was returned. The question and failed retrieval are retained for rerun; Atlas will not invent a conclusion."
    )
    research.confidence = (
        round(sum(f.confidence for f in findings) / len(findings), 2) if findings else 0
    )
    research.status = "completed"
    research.completed_at = datetime.now(UTC)
    db.commit()
    event(
        db,
        research.id,
        "synthesize",
        "completed",
        began,
        confidence=research.confidence,
        provider="fireworks" if providers["fireworks"] else "deterministic_fallback",
        contradiction_check="Full-text claim checking is queued for the production extractor.",
    )
    db.refresh(research)
    return research
