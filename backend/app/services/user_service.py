import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_id(db: Session, user_id: Union[uuid.UUID, str]) -> Optional[User]:
    """Retrieves a user by their UUID primary key."""
    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except ValueError:
            return None
    stmt = select(User).where(User.id == user_id)
    return db.scalars(stmt).first()


def get_user_by_github_id(db: Session, github_user_id: str) -> Optional[User]:
    """Retrieves a user by their unique GitHub user ID."""
    stmt = select(User).where(User.github_user_id == str(github_user_id))
    return db.scalars(stmt).first()


def get_or_create_user(
    db: Session,
    gh_profile: Dict[str, Any],
    email: Optional[str] = None
) -> User:
    """
    Finds an existing user by github_user_id or creates a new user.
    Updates login handle, name, email, avatar, and updated_at timestamp.
    """
    github_user_id = str(gh_profile["id"])
    github_login = gh_profile.get("login") or "github-user"
    name = gh_profile.get("name")
    resolved_email = email or gh_profile.get("email")
    avatar_url = gh_profile.get("avatar_url")

    user = get_user_by_github_id(db, github_user_id)

    if user:
        user.github_login = github_login
        user.name = name
        if resolved_email:
            user.email = resolved_email
        user.avatar_url = avatar_url
        user.updated_at = datetime.now(timezone.utc)
    else:
        user = User(
            github_user_id=github_user_id,
            github_login=github_login,
            name=name,
            email=resolved_email,
            avatar_url=avatar_url,
        )
        db.add(user)

    db.commit()
    db.refresh(user)
    return user
