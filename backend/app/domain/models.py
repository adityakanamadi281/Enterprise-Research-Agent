from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from app.config import settings


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    projects: Mapped[list["Project"]] = relationship(back_populates="organization")


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    organization: Mapped[Organization] = relationship(back_populates="projects")
    sessions: Mapped[list["ResearchSession"]] = relationship(back_populates="project")


class ResearchSession(Base):
    __tablename__ = "research_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    question: Mapped[str] = mapped_column(Text)
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(24), default="queued")
    confidence: Mapped[float] = mapped_column(Float, default=0)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sources: Mapped[list["Source"]] = relationship(
        back_populates="research_session",
        cascade="all, delete-orphan",
        foreign_keys="Source.research_session_id",
    )
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="research_session", cascade="all, delete-orphan"
    )
    events: Mapped[list["RunEvent"]] = relationship(
        back_populates="research_session", cascade="all, delete-orphan"
    )
    project: Mapped[Project | None] = relationship(back_populates="sessions")
    reports: Mapped[list["Report"]] = relationship(back_populates="research_session")


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    research_session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"))
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    reliability_score: Mapped[float] = mapped_column(Float, default=0.5)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(64), default="web_article")
    is_primary: Mapped[bool] = mapped_column(default=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    first_seen_session_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_sessions.id"), nullable=True, index=True
    )
    research_session: Mapped[ResearchSession] = relationship(
        back_populates="sources",
        foreign_keys=[research_session_id],
    )
    findings: Mapped[list["Finding"]] = relationship(back_populates="source")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    research_session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(127))
    storage_path: Mapped[str] = mapped_column(Text)
    byte_size: Mapped[int] = mapped_column()
    extracted_characters: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    research_session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"))
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    claim: Mapped[str] = mapped_column(Text)
    evidence_span: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    classification: Mapped[str] = mapped_column(String(64), default="research_evidence")
    topic_key: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    stance: Mapped[str] = mapped_column(String(24), default="unclear")
    evidence_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    research_session: Mapped[ResearchSession] = relationship(back_populates="findings")
    source: Mapped[Source | None] = relationship(back_populates="findings")


class RunEvent(Base):
    __tablename__ = "run_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    research_session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"))
    step: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24))
    duration_ms: Mapped[float] = mapped_column(Float, default=0)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    research_session: Mapped[ResearchSession] = relationship(back_populates="events")


class EvidenceChunk(Base):
    """A durable, citable passage used for semantic reuse across research sessions."""

    __tablename__ = "evidence_chunks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    char_start: Mapped[int] = mapped_column(Integer)
    char_end: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ClaimComparison(Base):
    """Explicit support/conflict judgement between two retained findings."""

    __tablename__ = "claim_comparisons"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    research_session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"), index=True)
    finding_a_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), index=True)
    finding_b_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), index=True)
    relationship: Mapped[str] = mapped_column(String(24))
    explanation: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class SessionSourceLink(Base):
    __tablename__ = "session_source_links"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    research_session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    origin: Mapped[str] = mapped_column(String(24))  # fetched | reused | uploaded
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Entity(Base):
    __tablename__ = "entities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    research_session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), default="concept")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    canonical_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    first_seen_research_session_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_sessions.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    research_session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"), index=True)
    source_entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"))
    target_entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"))
    relation_type: Mapped[str] = mapped_column(String(64), default="supported_by")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    entity_a_id: Mapped[str | None] = mapped_column(
        ForeignKey("entities.id"), nullable=True, index=True
    )
    entity_b_id: Mapped[str | None] = mapped_column(
        ForeignKey("entities.id"), nullable=True, index=True
    )
    relationship_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_finding_id: Mapped[str | None] = mapped_column(
        ForeignKey("findings.id"), nullable=True
    )
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)


class EntityMention(Base):
    __tablename__ = "entity_mentions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), index=True)
    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), index=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    research_session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"), index=True)
    mention_text: Mapped[str] = mapped_column(Text)
    char_start: Mapped[int] = mapped_column(Integer)
    char_end: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class LlmCall(Base):
    __tablename__ = "llm_calls"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    research_session_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_sessions.id"), nullable=True, index=True
    )
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    node: Mapped[str] = mapped_column(String(32), default="other")
    provider: Mapped[str] = mapped_column(String(32))
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    call_type: Mapped[str] = mapped_column(String(24))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(24))
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    research_session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    content: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    research_session: Mapped[ResearchSession] = relationship(back_populates="reports")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    action: Mapped[str] = mapped_column(String(96), index=True)
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(36))
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


engine = create_engine(
    settings().database_url,
    connect_args={"check_same_thread": False}
    if settings().database_url.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)
    # The starter release used create_all. Keep local persisted SQLite demos forward compatible.
    if engine.dialect.name == "sqlite":
        columns = {column["name"] for column in inspect(engine).get_columns("research_sessions")}
        with engine.begin() as connection:
            if "project_id" not in columns:
                connection.execute(
                    text("ALTER TABLE research_sessions ADD COLUMN project_id VARCHAR(36)")
                )
            source_columns = {column["name"] for column in inspect(engine).get_columns("sources")}
            for name, ddl in {
                "canonical_url": "TEXT",
                "content_hash": "VARCHAR(64)",
                "source_type": "VARCHAR(64) DEFAULT 'web_article'",
                "is_primary": "BOOLEAN DEFAULT 0",
                "retrieved_at": "DATETIME",
                "first_seen_session_id": "VARCHAR(36)",
            }.items():
                if name not in source_columns:
                    connection.execute(text(f"ALTER TABLE sources ADD COLUMN {name} {ddl}"))
            finding_columns = {column["name"] for column in inspect(engine).get_columns("findings")}
            for name, ddl in {
                "topic_key": "VARCHAR(160)",
                "stance": "VARCHAR(24) DEFAULT 'unclear'",
                "evidence_start": "INTEGER",
                "evidence_end": "INTEGER",
            }.items():
                if name not in finding_columns:
                    connection.execute(text(f"ALTER TABLE findings ADD COLUMN {name} {ddl}"))
            entity_columns = {column["name"] for column in inspect(engine).get_columns("entities")}
            for name, ddl in {
                "canonical_key": "VARCHAR(255)",
                "first_seen_research_session_id": "VARCHAR(36)",
            }.items():
                if name not in entity_columns:
                    connection.execute(text(f"ALTER TABLE entities ADD COLUMN {name} {ddl}"))
            relationship_columns = {
                column["name"] for column in inspect(engine).get_columns("entity_relationships")
            }
            for name, ddl in {
                "entity_a_id": "VARCHAR(36)",
                "entity_b_id": "VARCHAR(36)",
                "relationship_type": "VARCHAR(64)",
                "evidence_finding_id": "VARCHAR(36)",
                "explanation": "TEXT",
            }.items():
                if name not in relationship_columns:
                    connection.execute(
                        text(f"ALTER TABLE entity_relationships ADD COLUMN {name} {ddl}")
                    )
