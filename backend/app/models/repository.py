import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Boolean, DateTime, Index, Uuid, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.analysis import AnalysisRun


class Repository(Base):
    """
    SQLAlchemy model representing an ingested GitHub repository record.
    """
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        doc="Primary UUID identifier for the repository"
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Owner user UUID who analyzed or created this repository record"
    )

    github_url: Mapped[str] = mapped_column(
        String(512),
        index=True,
        nullable=False,
        doc="Canonical GitHub URL of the repository"
    )

    owner: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
        doc="Repository owner username or organization"
    )

    name: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
        doc="Repository name"
    )

    default_branch: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        default="main",
        doc="Default branch name (e.g. main or master)"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Repository description text"
    )

    stars: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="GitHub stargazer count"
    )

    forks: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="GitHub fork count"
    )

    open_issues: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="GitHub open issues count"
    )

    language: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Primary detected programming language"
    )

    is_private: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="True if the repository is private, false otherwise"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when this repository record was first created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp when this repository record was last updated"
    )

    last_analyzed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of the most recent analysis run completed"
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="repositories",
        doc="Owner user entity"
    )

    analyses: Mapped[List["AnalysisRun"]] = relationship(
        "AnalysisRun",
        back_populates="repository",
        cascade="all, delete-orphan",
        order_by="desc(AnalysisRun.created_at)",
        doc="Historical analysis runs associated with this repository"
    )

    __table_args__ = (
        Index("ix_repositories_owner_name", "owner", "name"),
        Index("uq_repositories_user_id_github_url", "user_id", "github_url", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Repository {self.owner}/{self.name} (id={self.id})>"
