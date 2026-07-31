from datetime import UTC, datetime
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.api.security import require_api_key
from app.domain.models import (
    AuditLog,
    Entity,
    EntityRelationship,
    Document,
    Finding,
    Organization,
    Project,
    Report,
    ResearchSession,
    RunEvent,
    SessionLocal,
    Source,
)
from app.services.research import run_research
from app.services.audit import record_audit
from app.services.documents import store_and_extract
from app.services.providers import qdrant_upsert

router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ResearchRequest(BaseModel):
    question: str = Field(min_length=12, max_length=500)


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
    item = run_research(db, payload.question.strip())
    record_audit(db, "research.created", "research_session", item.id, None, question=item.question)
    return detail(item, db)


@router.post("/documents/upload", status_code=201)
async def upload_documents(files: list[UploadFile] = File(...), db: Session = Depends(db_session)):
    """Persist user documents as evidence that can be inspected and vector-indexed."""
    if not files or len(files) > 5:
        raise HTTPException(422, "Upload between one and five files per request")
    uploaded = []
    for upload in files:
        path, extracted, byte_size = await store_and_extract(upload)
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
    return {
        "sessions": db.scalar(select(func.count(ResearchSession.id))),
        "sources": db.scalar(select(func.count(Source.id))),
        "findings": db.scalar(select(func.count(Finding.id))),
        "events": db.scalar(select(func.count(RunEvent.id))),
        "completed_runs": completed,
        "average_confidence": round(average_confidence, 2),
        "measured_at": datetime.now(UTC),
    }


@router.get("/knowledge/search")
def search_knowledge(q: str = "", db: Session = Depends(db_session)):
    """Search durable research memory. Vector retrieval can replace this adapter later."""
    term = q.strip()
    if len(term) < 2:
        return []
    pattern = f"%{term}%"
    findings = db.scalars(
        select(Finding)
        .where(or_(Finding.claim.ilike(pattern), Finding.evidence_span.ilike(pattern)))
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
        "generated_at": datetime.now(UTC),
        "disclaimer": "This report summarizes retained evidence. It is not a substitute for primary-source review.",
    }
    saved = Report(research_session_id=item.id, title=payload.title.strip(), content=content)
    db.add(saved)
    db.commit()
    record_audit(db, "report.generated", "report", saved.id, None, research_session_id=item.id)
    return {"id": saved.id, **content}


@router.get("/research/{id}/graph")
def research_graph(id: str, db: Session = Depends(db_session)):
    if not db.get(ResearchSession, id):
        raise HTTPException(404, "Research session not found")
    entities = db.scalars(select(Entity).where(Entity.research_session_id == id)).all()
    relationships = db.scalars(
        select(EntityRelationship).where(EntityRelationship.research_session_id == id)
    ).all()
    return {
        "nodes": [
            {"id": x.id, "label": x.name, "type": x.entity_type, "confidence": x.confidence}
            for x in entities
        ],
        "edges": [
            {
                "id": x.id,
                "source": x.source_entity_id,
                "target": x.target_entity_id,
                "type": x.relation_type,
                "confidence": x.confidence,
            }
            for x in relationships
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


def detail(item, db):
    sources = db.scalars(select(Source).where(Source.research_session_id == item.id)).all()
    findings = db.scalars(
        select(Finding)
        .where(Finding.research_session_id == item.id)
        .order_by(Finding.confidence.desc())
    ).all()
    events = db.scalars(
        select(RunEvent)
        .where(RunEvent.research_session_id == item.id)
        .order_by(RunEvent.created_at)
    ).all()
    return {
        "id": item.id,
        "question": item.question,
        "status": item.status,
        "confidence": item.confidence,
        "conclusion": item.conclusion,
        "created_at": item.created_at,
        "sources": [
            {
                "id": s.id,
                "title": s.title,
                "url": s.url,
                "publisher": s.publisher,
                "published_at": s.published_at,
                "reliability_score": s.reliability_score,
            }
            for s in sources
        ],
        "findings": [
            {
                "id": f.id,
                "claim": f.claim,
                "evidence_span": f.evidence_span,
                "confidence": f.confidence,
                "classification": f.classification,
                "source_id": f.source_id,
            }
            for f in findings
        ],
        "events": [
            {
                "step": e.step,
                "status": e.status,
                "duration_ms": e.duration_ms,
                "details": e.details,
                "created_at": e.created_at,
            }
            for e in events
        ],
    }
