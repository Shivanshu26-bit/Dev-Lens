import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.repository import Repository


def get_repository_by_url(db: Session, github_url: str) -> Optional[Repository]:
    """
    Retrieves a repository record by its canonical GitHub URL.
    """
    normalized_url = github_url.strip().rstrip("/")
    stmt = select(Repository).where(Repository.github_url == normalized_url)
    return db.scalars(stmt).first()


def get_repository_by_id(db: Session, repository_id: Union[uuid.UUID, str]) -> Optional[Repository]:
    """
    Retrieves a repository record by its UUID primary key.
    """
    if isinstance(repository_id, str):
        try:
            repository_id = uuid.UUID(repository_id)
        except ValueError:
            return None
    stmt = select(Repository).where(Repository.id == repository_id)
    return db.scalars(stmt).first()


def create_or_update_repository(
    db: Session,
    metadata: Dict[str, Any],
    github_url: str
) -> Repository:
    """
    Creates a new Repository record or updates existing metadata.
    """
    normalized_url = github_url.strip().rstrip("/")
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
        repo.updated_at = datetime.now(timezone.utc)
    else:
        repo = Repository(
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
