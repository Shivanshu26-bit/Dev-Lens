import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.repository import Repository


def get_repository_by_url(db: Session, github_url: str) -> Optional[Repository]:
    """
    Retrieves the first repository record matching canonical GitHub URL.
    Maintained for backwards compatibility.
    """
    normalized_url = github_url.strip().rstrip("/")
    stmt = select(Repository).where(Repository.github_url == normalized_url)
    return db.scalars(stmt).first()


def get_repository_by_user_and_url(
    db: Session,
    user_id: Optional[Union[uuid.UUID, str]],
    github_url: str
) -> Optional[Repository]:
    """
    Retrieves a repository record owned by a specific user matching canonical GitHub URL.
    """
    normalized_url = github_url.strip().rstrip("/")
    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except ValueError:
            return None

    if user_id is not None:
        stmt = select(Repository).where(
            Repository.user_id == user_id,
            Repository.github_url == normalized_url
        )
    else:
        stmt = select(Repository).where(
            Repository.user_id.is_(None),
            Repository.github_url == normalized_url
        )
    return db.scalars(stmt).first()


def get_repository_by_id(
    db: Session,
    repository_id: Union[uuid.UUID, str],
    user_id: Optional[Union[uuid.UUID, str]] = None
) -> Optional[Repository]:
    """
    Retrieves a repository record by UUID. If user_id is supplied, enforces ownership.
    """
    if isinstance(repository_id, str):
        try:
            repository_id = uuid.UUID(repository_id)
        except ValueError:
            return None

    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except ValueError:
            return None

    stmt = select(Repository).where(Repository.id == repository_id)
    if user_id is not None:
        stmt = stmt.where(Repository.user_id == user_id)

    return db.scalars(stmt).first()


def create_or_update_repository(
    db: Session,
    metadata: Dict[str, Any],
    github_url: str,
    user_id: Optional[Union[uuid.UUID, str]] = None
) -> Repository:
    """
    Creates a new Repository record owned by user_id or updates existing metadata.
    """
    normalized_url = github_url.strip().rstrip("/")
    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except ValueError:
            user_id = None

    if user_id is not None:
        repo = get_repository_by_user_and_url(db, user_id, normalized_url)
    else:
        repo = get_repository_by_url(db, normalized_url)

    owner = metadata.get("owner") or "unknown"
    name = metadata.get("name") or "unknown"
    default_branch = metadata.get("default_branch", "main")
    description = metadata.get("description")
    stars = int(metadata.get("stars", 0))
    forks = int(metadata.get("forks", 0))
    open_issues = int(metadata.get("open_issues", 0))
    language = metadata.get("language")
    is_private = bool(metadata.get("visibility") == "private" or metadata.get("is_private", False))

    if repo:
        repo.owner = owner
        repo.name = name
        repo.default_branch = default_branch
        repo.description = description
        repo.stars = stars
        repo.forks = forks
        repo.open_issues = open_issues
        repo.language = language
        repo.is_private = is_private
        if user_id is not None and repo.user_id is None:
            repo.user_id = user_id
        repo.updated_at = datetime.now(timezone.utc)
    else:
        repo = Repository(
            user_id=user_id,
            github_url=normalized_url,
            owner=owner,
            name=name,
            default_branch=default_branch,
            description=description,
            stars=stars,
            forks=forks,
            open_issues=open_issues,
            language=language,
            is_private=is_private,
        )
        db.add(repo)

    db.commit()
    db.refresh(repo)
    return repo


def update_last_analyzed(
    db: Session,
    repository_id: Union[uuid.UUID, str],
    analyzed_at: Optional[datetime] = None
) -> Optional[Repository]:
    """
    Updates the last_analyzed_at timestamp for a repository.
    """
    repo = get_repository_by_id(db, repository_id)
    if not repo:
        return None

    repo.last_analyzed_at = analyzed_at or datetime.now(timezone.utc)
    repo.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(repo)
    return repo
