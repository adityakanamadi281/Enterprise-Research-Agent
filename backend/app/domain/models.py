from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text, create_engine, inspect, text
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
        back_populates="research_session", cascade="all, delete-orphan"
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
    research_session: Mapped[ResearchSession] = relationship(back_populates="sources")
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


class Entity(Base):
    __tablename__ = "entities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    research_session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), default="concept")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    research_session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"), index=True)
    source_entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"))
    target_entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"))
    relation_type: Mapped[str] = mapped_column(String(64), default="supported_by")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)


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
        if "project_id" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE research_sessions ADD COLUMN project_id VARCHAR(36)")
                )
