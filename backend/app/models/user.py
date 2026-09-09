import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """
    SQLAlchemy model representing an authenticated DevLens user account (GitHub OAuth).
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        doc="Primary UUID identifier for the user"
    )

    github_user_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        doc="Unique GitHub user numeric ID stored as string"
    )

    github_login: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
        doc="GitHub username/login handle"
    )

    name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="User display or full name"
    )

    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Primary verified email address"
    )

    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        doc="GitHub profile avatar image URL"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when this user record was first created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp when this user record was last updated"
    )

    # Relationships
    repositories: Mapped[List["Repository"]] = relationship(
        "Repository",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Repository.created_at)",
        doc="Repositories analyzed by this user"
    )

    sessions: Mapped[List["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(UserSession.created_at)",
        doc="Active or revoked user sessions"
    )

    def __repr__(self) -> str:
        return f"<User {self.github_login} (id={self.id})>"

