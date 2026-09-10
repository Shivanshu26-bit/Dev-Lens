import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union, List
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.repository import Repository
from app.schemas.persistence_schemas import RepositoryListItemResponse, LatestAnalysisSummary


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


def get_user_repositories(
    db: Session,
    user_id: Union[uuid.UUID, str],
    limit: int = 50,
    offset: int = 0
) -> List[RepositoryListItemResponse]:
    """
    Retrieves repositories owned by user_id, ordered by most recently analyzed / updated first.
    Populates latest analysis run metadata and summary metrics for each repository.
    """
    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except ValueError:
            return []

    stmt = (
        select(Repository)
        .where(Repository.user_id == user_id)
        .order_by(
            func.coalesce(Repository.last_analyzed_at, Repository.updated_at, Repository.created_at).desc()
        )
        .limit(limit)
        .offset(offset)
    )
    repos = db.scalars(stmt).all()

    result: List[RepositoryListItemResponse] = []
    for repo in repos:
        latest_analysis = None
        if repo.analyses:
            latest_run = repo.analyses[0]
            total_lines = None
            code_lines = None
            total_files = None
            findings_count = None

            if latest_run.metrics:
                total_lines = latest_run.metrics.get("total_lines")
                code_lines = latest_run.metrics.get("code_lines")
            elif latest_run.deterministic_result and isinstance(latest_run.deterministic_result, dict):
                metrics_dict = latest_run.deterministic_result.get("metrics") or {}
                total_lines = metrics_dict.get("total_lines")
                code_lines = metrics_dict.get("code_lines")

            if latest_run.deterministic_result and isinstance(latest_run.deterministic_result, dict):
                summary_dict = latest_run.deterministic_result.get("summary") or {}
                total_files = summary_dict.get("total_files")
                findings_list = latest_run.deterministic_result.get("findings") or []
                findings_count = len(findings_list)
            elif latest_run.findings is not None:
                findings_count = len(latest_run.findings)

            latest_analysis = LatestAnalysisSummary(
                id=latest_run.id,
                status=latest_run.status,
                analysis_type=latest_run.analysis_type,
                created_at=latest_run.created_at,
                completed_at=latest_run.completed_at,
                error_message=latest_run.error_message,
                total_lines=total_lines,
                code_lines=code_lines,
                total_files=total_files,
                findings_count=findings_count
            )

        item = RepositoryListItemResponse(
            id=repo.id,
            github_url=repo.github_url,
            owner=repo.owner,
            name=repo.name,
            default_branch=repo.default_branch,
            description=repo.description,
            stars=repo.stars,
            forks=repo.forks,
            open_issues=repo.open_issues,
            language=repo.language,
            is_private=repo.is_private,
            created_at=repo.created_at,
            updated_at=repo.updated_at,
            last_analyzed_at=repo.last_analyzed_at,
            latest_analysis=latest_analysis
        )
        result.append(item)

    return result


def delete_repository(
    db: Session,
    repository_id: Union[uuid.UUID, str],
    user_id: Union[uuid.UUID, str]
) -> bool:
    """
    Deletes a repository record and all associated analysis runs owned by user_id.
    Returns True if found and deleted, False otherwise.
    """
    repo = get_repository_by_id(db, repository_id, user_id=user_id)
    if not repo:
        return False

    db.delete(repo)
    db.commit()
    return True
