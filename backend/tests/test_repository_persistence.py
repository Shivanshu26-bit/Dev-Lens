import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.services.repository_persistence import (
    create_or_update_repository,
    get_repository_by_url,
    get_repository_by_id,
    update_last_analyzed,
)


def test_create_or_update_repository_new(db_session: Session):
    """Test creating a new repository record via persistence service."""
    metadata = {
        "owner": "fastapi",
        "name": "fastapi",
        "default_branch": "master",
        "description": "FastAPI framework, high performance",
        "stars": 75000,
        "forks": 6000,
        "open_issues": 150,
        "language": "Python",
        "visibility": "public",
    }
    repo = create_or_update_repository(db_session, metadata, "https://github.com/fastapi/fastapi/")
    assert repo.id is not None
    assert repo.github_url == "https://github.com/fastapi/fastapi"  # Trailing slash stripped
    assert repo.owner == "fastapi"
    assert repo.name == "fastapi"
    assert repo.stars == 75000
    assert repo.default_branch == "master"


def test_create_or_update_repository_existing(db_session: Session):
    """Test updating existing repository record when called again."""
    metadata = {
        "owner": "fastapi",
        "name": "fastapi",
        "stars": 75000,
        "forks": 6000,
        "language": "Python",
    }
    repo1 = create_or_update_repository(db_session, metadata, "https://github.com/fastapi/fastapi")

    # Update stars and forks
    updated_metadata = {
        "owner": "fastapi",
        "name": "fastapi",
        "stars": 80000,
        "forks": 6500,
        "language": "Python",
    }
    repo2 = create_or_update_repository(db_session, updated_metadata, "https://github.com/fastapi/fastapi")

    assert repo1.id == repo2.id
    assert repo2.stars == 80000
    assert repo2.forks == 6500


def test_get_repository_by_url(db_session: Session):
    """Test retrieval by URL handles slash variations and missing repos."""
    metadata = {"owner": "tiangolo", "name": "sqlmodel", "stars": 12000}
    create_or_update_repository(db_session, metadata, "https://github.com/tiangolo/sqlmodel")

    # Exact match
    found = get_repository_by_url(db_session, "https://github.com/tiangolo/sqlmodel")
    assert found is not None
    assert found.name == "sqlmodel"

    # Trailing slash match
    found_slash = get_repository_by_url(db_session, "https://github.com/tiangolo/sqlmodel/")
    assert found_slash is not None
    assert found_slash.id == found.id

    # Non-existent
    assert get_repository_by_url(db_session, "https://github.com/nonexistent/repo") is None


def test_get_repository_by_id(db_session: Session):
    """Test retrieval by UUID and string representation."""
    metadata = {"owner": "psf", "name": "requests", "stars": 50000}
    repo = create_or_update_repository(db_session, metadata, "https://github.com/psf/requests")

    # By UUID
    by_uuid = get_repository_by_id(db_session, repo.id)
    assert by_uuid is not None
    assert by_uuid.id == repo.id

    # By String
    by_str = get_repository_by_id(db_session, str(repo.id))
    assert by_str is not None
    assert by_str.id == repo.id

    # Invalid UUID string
    assert get_repository_by_id(db_session, "invalid-uuid-string") is None

    # Missing UUID
    assert get_repository_by_id(db_session, uuid.uuid4()) is None


def test_update_last_analyzed(db_session: Session):
    """Test updating last_analyzed timestamp."""
    metadata = {"owner": "pallets", "name": "flask", "stars": 65000}
    repo = create_or_update_repository(db_session, metadata, "https://github.com/pallets/flask")
    assert repo.last_analyzed_at is None

    now = datetime.now(timezone.utc)
    updated = update_last_analyzed(db_session, repo.id, analyzed_at=now)
    assert updated is not None
    assert updated.last_analyzed_at is not None

    # Non-existent repo returns None
    assert update_last_analyzed(db_session, uuid.uuid4()) is None
