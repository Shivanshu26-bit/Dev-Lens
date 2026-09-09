import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Text, DateTime, ForeignKey, Uuid, JSON, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base


class AnalysisStatus(str, Enum):
    """Lifecycle statuses for an analysis run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisType(str, Enum):
    """Categorical type of analysis executed."""
    DETERMINISTIC = "deterministic"
    AI = "ai"
    FULL = "full"


# Cross-dialect JSONB type that falls back to standard JSON on SQLite
JSONBType = JSON().with_variant(JSONB, "postgresql")


class AnalysisRun(Base):
    """
    SQLAlchemy model representing a specific analysis execution run for a repository.
    """
    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        doc="Primary UUID identifier for the analysis run"
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key reference to parent repository record"
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default=AnalysisStatus.PENDING.value,
        nullable=False,
        index=True,
        doc="Execution status (pending, running, completed, failed)"
    )

    analysis_type: Mapped[str] = mapped_column(
        String(50),
        default=AnalysisType.DETERMINISTIC.value,
        nullable=False,
        doc="Type of analysis executed (deterministic, ai, full)"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        doc="Timestamp when this analysis run was scheduled/created"
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when analysis processing actually began"
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when analysis processing completed or failed"
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Safe error message if analysis status is failed"
    )

    # JSONB payloads
    deterministic_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONBType,
        nullable=True,
        doc="Complete deterministic Phase 3 report payload"
    )

    ai_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONBType,
        nullable=True,
        doc="Complete Phase 4 AI analysis report payload"
    )

    metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONBType,
        nullable=True,
        doc="Extracted line and file metrics"
    )

    findings: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONBType,
        nullable=True,
        doc="Extracted security and code-quality findings"
    )

    languages: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONBType,
        nullable=True,
        doc="Language distribution summary list"
    )

    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONBType,
        nullable=True,
        doc="Analysis metadata (files analyzed, skipped reasons, limits)"
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(
        "Repository",
        back_populates="analyses",
        doc="Parent repository entity"
    )

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        """Enforces that status belongs to valid AnalysisStatus members."""
        valid_statuses = {s.value for s in AnalysisStatus}
        if value not in valid_statuses:
            raise ValueError(f"Invalid analysis status '{value}'. Supported statuses: {valid_statuses}")
        return value

    @validates("analysis_type")
    def validate_analysis_type(self, key: str, value: str) -> str:
        """Enforces that analysis_type belongs to valid AnalysisType members."""
        valid_types = {t.value for t in AnalysisType}
        if value not in valid_types:
            raise ValueError(f"Invalid analysis type '{value}'. Supported types: {valid_types}")
        return value

    def __repr__(self) -> str:
        return f"<AnalysisRun {self.id} (repo={self.repository_id}, status={self.status})>"
