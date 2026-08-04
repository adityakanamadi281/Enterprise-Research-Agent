import asyncio
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.api.security import require_api_key
from app.domain.models import (
    AuditLog,
    ClaimComparison,
    Entity,
    EntityMention,
    EntityRelationship,
    LlmCall,
    Document,
    Finding,
    Organization,
    Project,
    Report,
    ResearchSession,
    RunEvent,
    SessionSourceLink,
    SessionLocal,
    Source,
)
from app.services.research import run_research
from app.services.audit import record_audit
from app.services.documents import store_and_extract
from app.services.providers import qdrant_search, qdrant_upsert

router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ResearchRequest(BaseModel):
    question: str = Field(min_length=12, max_length=500)
    project_id: str | None = None


class ReportRequest(BaseModel):
    title: str = Field(min_length=3, max_length=180)


class OrganizationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)


class ProjectRequest(BaseModel):
    organization_id: str
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2_000)


@router.get("/health")
def health():
    return {"status": "ok", "service": "atlas-api"}


@router.post("/research", status_code=201)
def create(payload: ResearchRequest, db: Session = Depends(db_session)):
    if payload.project_id and not db.get(Project, payload.project_id):
        raise HTTPException(404, "Project not found")
    item = run_research(db, payload.question.strip())
    item.project_id = payload.project_id
    db.commit()
    record_audit(db, "research.created", "research_session", item.id, None, question=item.question)
    return detail(item, db)


def run_queued_research(session_id: str, question: str) -> None:
    """Background entry point intentionally creates its own request-independent database session."""
    db = SessionLocal()
    try:
        run_research(db, question, session_id=session_id)
        record_audit(db, "research.completed", "research_session", session_id, None)
    finally:
        db.close()


@router.post("/research/async", status_code=202)
def create_async(
    payload: ResearchRequest, tasks: BackgroundTasks, db: Session = Depends(db_session)
):
    if payload.project_id and not db.get(Project, payload.project_id):
        raise HTTPException(404, "Project not found")
    item = ResearchSession(
        question=payload.question.strip(), project_id=payload.project_id, status="queued"
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    tasks.add_task(run_queued_research, item.id, item.question)
    record_audit(db, "research.queued", "research_session", item.id, None, question=item.question)
    return detail(item, db)


@router.get("/research/{id}/events/stream")
async def stream_events(id: str, db: Session = Depends(db_session)):
    if not db.get(ResearchSession, id):
        raise HTTPException(404, "Research session not found")

    async def event_stream():
        last_count = -1
        while True:
            live = SessionLocal()
            try:
                item = live.get(ResearchSession, id)
                events = list(
                    live.scalars(
                        select(RunEvent)
                        .where(RunEvent.research_session_id == id)
                        .order_by(RunEvent.created_at)
                    )
                )
                if len(events) != last_count:
                    last_count = len(events)
                    yield (
                        "data: "
                        + __import__("json").dumps(
                            {
                                "status": item.status,
                                "events": [
                                    {
                                        "step": e.step,
                                        "status": e.status,
                                        "details": e.details,
                                        "created_at": e.created_at.isoformat(),
                                    }
                                    for e in events
                                ],
                            },
                            default=str,
                        )
                        + "\n\n"
                    )
                if item.status in {"completed", "failed"}:
                    break
            finally:
                live.close()
            await asyncio.sleep(0.75)

    return StreamingResponse(
        event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
    )


@router.post("/documents/upload", status_code=201)
async def upload_documents(
    files: list[UploadFile] = File(...),
    research_session_id: Annotated[str | None, Form()] = None,
    db: Session = Depends(db_session),
):
    """Persist user documents as evidence that can be inspected and vector-indexed."""
    if not files or len(files) > 5:
        raise HTTPException(422, "Upload between one and five files per request")
    uploaded = []
    for upload in files:
        path, extracted, byte_size = await store_and_extract(upload)
        session = db.get(ResearchSession, research_session_id) if research_session_id else None
        if research_session_id and not session:
            raise HTTPException(404, "Research session not found")
        if not session:
            session = ResearchSession(
                question=f"User-provided evidence: {upload.filename or 'uploaded document'}",
                status="completed",
                conclusion="Document ingested and available as durable research evidence.",
                confidence=0.8,
                completed_at=datetime.now(UTC),
            )
            db.add(session)
            db.commit()
        document = Document(
            research_session_id=session.id,
            original_filename=upload.filename or "upload",
            content_type=upload.content_type or "application/octet-stream",
            storage_path=str(path),
            byte_size=byte_size,
            extracted_characters=len(extracted),
        )
        db.add(document)
        db.commit()
        source = Source(
            research_session_id=session.id,
            title=document.original_filename,
            url=f"document://{document.id}",
            publisher="user_upload",
            abstract=extracted[:8000],
            reliability_score=0.8,
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        finding = Finding(
            research_session_id=session.id,
            source_id=source.id,
            claim=f"Evidence extracted from {document.original_filename}",
            evidence_span=extracted[:800],
            confidence=0.8,
            classification="user_provided_document",
        )
        db.add(finding)
        db.commit()
        try:
            indexed = qdrant_upsert(
                source.id,
                extracted,
                {
                    "research_session_id": session.id,
                    "source_id": source.id,
                    "document_id": document.id,
                    "kind": "user_upload",
                },
            )
        except Exception:
            indexed = False
        record_audit(
            db,
            "document.uploaded",
            "document",
            document.id,
            None,
            filename=document.original_filename,
        )
        uploaded.append(
            {
                "document_id": document.id,
                "session_id": session.id,
                "filename": document.original_filename,
                "characters": document.extracted_characters,
                "vector_indexed": indexed,
            }
        )
    return {"documents": uploaded}


@router.post("/organizations", status_code=201)
def create_organization(payload: OrganizationRequest, db: Session = Depends(db_session)):
    organization = Organization(name=payload.name.strip())
    db.add(organization)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(409, "Organization name already exists") from exc
    record_audit(db, "organization.created", "organization", organization.id, None)
    return {"id": organization.id, "name": organization.name, "created_at": organization.created_at}


@router.post("/projects", status_code=201)
def create_project(payload: ProjectRequest, db: Session = Depends(db_session)):
    if not db.get(Organization, payload.organization_id):
        raise HTTPException(404, "Organization not found")
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    record_audit(db, "project.created", "project", project.id, None)
    return {"id": project.id, "organization_id": project.organization_id, "name": project.name}


@router.get("/projects")
def list_projects(db: Session = Depends(db_session)):
    projects = db.scalars(select(Project).order_by(Project.created_at.desc())).all()
    return [{"id": x.id, "organization_id": x.organization_id, "name": x.name} for x in projects]


@router.get("/research")
def listing(db: Session = Depends(db_session)):
    rows = db.scalars(
        select(ResearchSession).order_by(ResearchSession.created_at.desc()).limit(50)
    ).all()
    return [
        {
            "id": x.id,
            "question": x.question,
            "status": x.status,
            "confidence": x.confidence,
            "created_at": x.created_at,
        }
        for x in rows
    ]


@router.get("/research/{id}")
def get(id: str, db: Session = Depends(db_session)):
    item = db.get(ResearchSession, id)
    if not item:
        raise HTTPException(404, "Research session not found")
    return detail(item, db)


@router.get("/metrics/overview")
def metrics(db: Session = Depends(db_session)):
    average_confidence = db.scalar(select(func.avg(ResearchSession.confidence))) or 0
    completed = db.scalar(
        select(func.count(ResearchSession.id)).where(ResearchSession.status == "completed")
    )
    calls = list(db.scalars(select(LlmCall)))
    latencies = sorted(call.latency_ms for call in calls)

    def percentile(value: float) -> float:
        if not latencies:
            return 0
        return round(latencies[min(len(latencies) - 1, max(0, int(len(latencies) * value) - 1))], 1)

    return {
        "sessions": db.scalar(select(func.count(ResearchSession.id))),
        "sources": db.scalar(select(func.count(Source.id))),
        "findings": db.scalar(select(func.count(Finding.id))),
        "events": db.scalar(select(func.count(RunEvent.id))),
        "completed_runs": completed,
        "average_confidence": round(average_confidence, 2),
        "measured_at": datetime.now(UTC).isoformat(),
        "llm": {
            "total_calls": len(calls),
            "total_tokens": sum(x.total_tokens or 0 for x in calls),
            "total_estimated_cost_usd": sum(x.estimated_cost_usd or 0 for x in calls),
            "provider_usage": {
                p: sum(1 for x in calls if x.provider == p) for p in ("fireworks", "groq")
            },
            "fallback_rate": round(sum(1 for x in calls if x.attempt_number == 2) / len(calls), 3)
            if calls
            else 0,
            "p50_latency_ms": percentile(0.5),
            "p95_latency_ms": percentile(0.95),
        },
    }


@router.get("/knowledge/search")
def search_knowledge(q: str = "", db: Session = Depends(db_session)):
    """Hybrid retrieval: Fireworks embeddings/Qdrant first, durable SQL fallback second."""
    term = q.strip()
    if len(term) < 2:
        return []
    pattern = f"%{term}%"
    vector_source_ids: list[str] = []
    try:
        vector_source_ids = [
            str(point.get("payload", {}).get("source_id")) for point in qdrant_search(term)
        ]
    except Exception:
        vector_source_ids = []
    findings = db.scalars(
        select(Finding)
        .where(
            or_(
                Finding.source_id.in_(vector_source_ids),
                Finding.claim.ilike(pattern),
                Finding.evidence_span.ilike(pattern),
            )
        )
        .order_by(Finding.confidence.desc())
        .limit(20)
    ).all()
    return [
        {
            "id": finding.id,
            "session_id": finding.research_session_id,
            "claim": finding.claim,
            "evidence_span": finding.evidence_span,
            "confidence": finding.confidence,
            "source_id": finding.source_id,
        }
        for finding in findings
    ]


@router.post("/research/{id}/report")
def executive_report(id: str, payload: ReportRequest, db: Session = Depends(db_session)):
    """Generate a deterministic, evidence-linked executive report from stored intelligence."""
    item = db.get(ResearchSession, id)
    if not item:
        raise HTTPException(404, "Research session not found")
    report = detail(item, db)
    content = {
        "title": payload.title,
        "research_question": report["question"],
        "executive_summary": report["conclusion"],
        "confidence": report["confidence"],
        "evidence_findings": report["findings"],
        "sources": report["sources"],
        "generated_at": datetime.now(UTC).isoformat(),
        "disclaimer": "This report summarizes retained evidence. It is not a substitute for primary-source review.",
    }
    saved = Report(research_session_id=item.id, title=payload.title.strip(), content=content)
    db.add(saved)
    db.commit()
    record_audit(db, "report.generated", "report", saved.id, None, research_session_id=item.id)
    return {"id": saved.id, **content}


@router.get("/research/{id}/graph")
def research_graph(id: str, entity_id: str | None = None, db: Session = Depends(db_session)):
    if not db.get(ResearchSession, id):
        raise HTTPException(404, "Research session not found")
    mentions = db.scalars(
        select(EntityMention).where(EntityMention.research_session_id == id)
    ).all()
    entity_ids = {mention.entity_id for mention in mentions}
    entities = (
        db.scalars(select(Entity).where(Entity.id.in_(entity_ids))).all() if entity_ids else []
    )
    relationships = db.scalars(
        select(EntityRelationship).where(EntityRelationship.research_session_id == id)
    ).all()
    if entity_id:
        relationships = [
            edge
            for edge in relationships
            if entity_id
            in {edge.entity_a_id, edge.entity_b_id, edge.source_entity_id, edge.target_entity_id}
        ]
        entity_ids = (
            {entity_id}
            | {edge.entity_a_id or edge.source_entity_id for edge in relationships}
            | {edge.entity_b_id or edge.target_entity_id for edge in relationships}
        )
        entities = [entity for entity in entities if entity.id in entity_ids]
    finding_map = {
        item.id: item
        for item in db.scalars(select(Finding).where(Finding.research_session_id == id)).all()
    }
    return {
        "nodes": [
            {
                "id": x.id,
                "label": x.name,
                "type": x.entity_type,
                "confidence": x.confidence,
                "mention_count": sum(1 for mention in mentions if mention.entity_id == x.id),
            }
            for x in entities
        ],
        "edges": [
            {
                "id": x.id,
                "source": x.entity_a_id or x.source_entity_id,
                "target": x.entity_b_id or x.target_entity_id,
                "type": x.relationship_type or x.relation_type,
                "confidence": x.confidence,
                "evidence_finding_id": x.evidence_finding_id,
                "evidence_span": finding_map[x.evidence_finding_id].evidence_span
                if x.evidence_finding_id in finding_map
                else None,
            }
            for x in relationships
        ],
    }


@router.get("/research/{id}/explain")
def explain_finding(id: str, finding_id: str, db: Session = Depends(db_session)):
    finding = db.get(Finding, finding_id)
    if not finding or finding.research_session_id != id:
        raise HTTPException(404, "Finding not found in research session")
    source = db.get(Source, finding.source_id) if finding.source_id else None
    comparisons = list(
        db.scalars(
            select(ClaimComparison).where(
                ClaimComparison.research_session_id == id,
                or_(
                    ClaimComparison.finding_a_id == finding_id,
                    ClaimComparison.finding_b_id == finding_id,
                ),
            )
        )
    )

    def render(comparison):
        other_id = (
            comparison.finding_b_id
            if comparison.finding_a_id == finding_id
            else comparison.finding_a_id
        )
        other = db.get(Finding, other_id)
        other_source = db.get(Source, other.source_id) if other and other.source_id else None
        return {
            "other_finding": {
                "id": other.id,
                "claim": other.claim,
                "evidence_span": other.evidence_span,
            }
            if other
            else None,
            "other_source": source_payload(other_source),
            "relationship": comparison.relationship,
            "explanation": comparison.explanation,
            "confidence": comparison.confidence,
        }

    related = [render(comparison) for comparison in comparisons]
    mentions = db.scalars(select(EntityMention).where(EntityMention.finding_id == finding_id)).all()
    entities = [
        {
            "name": db.get(Entity, mention.entity_id).name,
            "type": db.get(Entity, mention.entity_id).entity_type,
            "mention_text": mention.mention_text,
        }
        for mention in mentions
        if db.get(Entity, mention.entity_id)
    ]
    related_confidence = [finding.confidence] + [
        item["other_finding"] and db.get(Finding, item["other_finding"]["id"]).confidence
        for item in related
    ]
    contradictions = sum(1 for item in related if item["relationship"] == "contradict")
    base = sum(related_confidence) / len(related_confidence)
    final = round(max(0, base - 0.04 * contradictions), 2)
    return {
        "finding": {
            "id": finding.id,
            "claim": finding.claim,
            "evidence_span": finding.evidence_span,
            "evidence_start": finding.evidence_start,
            "evidence_end": finding.evidence_end,
            "source": source_payload(source),
        },
        "supporting_comparisons": [item for item in related if item["relationship"] == "support"],
        "contradicting_comparisons": [
            item for item in related if item["relationship"] == "contradict"
        ],
        "entities_involved": entities,
        "confidence_derivation": {
            "base_confidence": round(base, 2),
            "contradiction_count": contradictions,
            "penalty_applied": round(0.04 * contradictions, 2),
            "final_confidence": final,
            "formula": "max(0, mean(confidence) - 0.04 * contradiction_count)",
        },
    }


@router.get("/research/{id}/observability")
def observability(id: str, offset: int = 0, limit: int = 100, db: Session = Depends(db_session)):
    if not db.get(ResearchSession, id):
        raise HTTPException(404, "Research session not found")
    calls = list(
        db.scalars(
            select(LlmCall).where(LlmCall.research_session_id == id).order_by(LlmCall.created_at)
        )
    )
    by_node = {
        node: [call for call in calls if call.node == node]
        for node in {call.node for call in calls}
    }
    return {
        "total_calls": len(calls),
        "fallback_trigger_count": sum(call.attempt_number == 2 for call in calls),
        "total_tokens": sum(call.total_tokens or 0 for call in calls),
        "total_estimated_cost_usd": sum(call.estimated_cost_usd or 0 for call in calls),
        "by_node": {
            node: {
                "calls": len(items),
                "latency_ms": round(sum(x.latency_ms for x in items), 1),
                "average_latency_ms": round(sum(x.latency_ms for x in items) / len(items), 1),
            }
            for node, items in by_node.items()
        },
        "by_provider": {
            provider: sum(1 for call in calls if call.provider == provider)
            for provider in {call.provider for call in calls}
        },
        "calls": [
            {
                "id": call.id,
                "request_id": call.request_id,
                "node": call.node,
                "provider": call.provider,
                "model_name": call.model_name,
                "call_type": call.call_type,
                "total_tokens": call.total_tokens,
                "latency_ms": call.latency_ms,
                "status": call.status,
                "attempt_number": call.attempt_number,
                "error_message": call.error_message,
                "created_at": call.created_at,
            }
            for call in calls[offset : offset + min(limit, 200)]
        ],
    }


@router.get("/audit-logs")
def audit_logs(limit: int = 50, db: Session = Depends(db_session)):
    rows = db.scalars(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 200))
    ).all()
    return [
        {
            "id": row.id,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "created_at": row.created_at,
        }
        for row in rows
    ]


def source_payload(source: Source | None):
    if not source:
        return None
    return {
        "id": source.id,
        "title": source.title,
        "url": source.url,
        "publisher": source.publisher,
        "published_at": source.published_at.isoformat() if hasattr(source.published_at, "isoformat") else source.published_at,
        "reliability_score": source.reliability_score,
        "source_type": source.source_type,
        "is_primary": source.is_primary,
        "retrieved_at": source.retrieved_at.isoformat() if hasattr(source.retrieved_at, "isoformat") else source.retrieved_at,
    }


def detail(item, db):
    findings = db.scalars(
        select(Finding)
        .where(Finding.research_session_id == item.id)
        .order_by(Finding.confidence.desc())
    ).all()
    source_ids = {finding.source_id for finding in findings if finding.source_id}
    sources = (
        db.scalars(select(Source).where(Source.id.in_(source_ids))).all() if source_ids else []
    )
    comparisons = db.scalars(
        select(ClaimComparison).where(ClaimComparison.research_session_id == item.id)
    ).all()
    events = db.scalars(
        select(RunEvent)
        .where(RunEvent.research_session_id == item.id)
        .order_by(RunEvent.created_at)
    ).all()
    source_links = {
        link.source_id: link.origin
        for link in db.scalars(
            select(SessionSourceLink).where(SessionSourceLink.research_session_id == item.id)
        ).all()
    }
    return {
        "id": item.id,
        "question": item.question,
        "status": item.status,
        "confidence": item.confidence,
        "conclusion": item.conclusion,
        "created_at": item.created_at.isoformat() if hasattr(item.created_at, "isoformat") else item.created_at,
        "sources": [
            {**source_payload(s), "origin": source_links.get(s.id, "fetched")} for s in sources
        ],
        "findings": [
            {
                "id": f.id,
                "claim": f.claim,
                "evidence_span": f.evidence_span,
                "confidence": f.confidence,
                "classification": f.classification,
                "source_id": f.source_id,
                "topic_key": f.topic_key,
                "stance": f.stance,
                "evidence_start": f.evidence_start,
                "evidence_end": f.evidence_end,
            }
            for f in findings
        ],
        "events": [
            {
                "step": e.step,
                "status": e.status,
                "duration_ms": e.duration_ms,
                "details": e.details,
                "created_at": e.created_at.isoformat() if hasattr(e.created_at, "isoformat") else e.created_at,
            }
            for e in events
        ],
        "comparisons": [
            {
                "finding_a_id": c.finding_a_id,
                "finding_b_id": c.finding_b_id,
                "relationship": c.relationship,
                "explanation": c.explanation,
                "confidence": c.confidence,
            }
            for c in comparisons
        ],
    }
