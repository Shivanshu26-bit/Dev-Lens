import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.repository import Repository
from app.models.analysis import AnalysisRun, AnalysisStatus, AnalysisType
from app.services.repository_persistence import (
    create_or_update_repository,
    update_last_analyzed,
    get_user_repositories,
    delete_repository,
)
from app.services.analysis_persistence import (
    create_analysis_run,
    save_deterministic_results,
    mark_analysis_completed,
    mark_analysis_failed,
)

client = TestClient(app)


def test_list_repositories_empty(db_session: Session, override_current_user: User):
    """Test GET /api/repositories returns an empty list when user has zero repositories."""
    response = client.get("/api/repositories")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_list_repositories_multiple(db_session: Session, override_current_user: User):
    """Test GET /api/repositories returns all repositories owned by the authenticated user."""
    meta1 = {"owner": "testorg", "name": "repo-one", "stars": 10, "language": "TypeScript"}
    meta2 = {"owner": "testorg", "name": "repo-two", "stars": 25, "language": "Python"}

    repo1 = create_or_update_repository(
        db_session, meta1, "https://github.com/testorg/repo-one", user_id=override_current_user.id
    )
    repo2 = create_or_update_repository(
        db_session, meta2, "https://github.com/testorg/repo-two", user_id=override_current_user.id
    )

    response = client.get("/api/repositories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    repo_ids = [item["id"] for item in data]
    assert str(repo1.id) in repo_ids
    assert str(repo2.id) in repo_ids

    # Verify schema fields
    item = next(i for i in data if i["id"] == str(repo1.id))
    assert item["owner"] == "testorg"
    assert item["name"] == "repo-one"
    assert item["stars"] == 10
    assert item["language"] == "TypeScript"
    assert item["github_url"] == "https://github.com/testorg/repo-one"


def test_list_repositories_ordering(db_session: Session, override_current_user: User):
    """Test GET /api/repositories orders by last_analyzed_at / updated_at descending."""
    now = datetime.now(timezone.utc)
    meta_old = {"owner": "testorg", "name": "repo-old"}
    meta_recent = {"owner": "testorg", "name": "repo-recent"}

    repo_old = create_or_update_repository(
        db_session, meta_old, "https://github.com/testorg/repo-old", user_id=override_current_user.id
    )
    repo_recent = create_or_update_repository(
        db_session, meta_recent, "https://github.com/testorg/repo-recent", user_id=override_current_user.id
    )

    update_last_analyzed(db_session, repo_old.id, analyzed_at=now - timedelta(days=2))
    update_last_analyzed(db_session, repo_recent.id, analyzed_at=now)

    response = client.get("/api/repositories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Most recently analyzed must be first
    assert data[0]["id"] == str(repo_recent.id)
    assert data[1]["id"] == str(repo_old.id)


def test_list_repositories_latest_analysis_summary(db_session: Session, override_current_user: User):
    """Test GET /api/repositories populates latest_analysis summary metrics."""
    meta = {"owner": "testorg", "name": "repo-with-analysis"}
    repo = create_or_update_repository(
        db_session, meta, "https://github.com/testorg/repo-with-analysis", user_id=override_current_user.id
    )

    run1 = create_analysis_run(db_session, repo.id, AnalysisType.DETERMINISTIC.value)
    save_deterministic_results(db_session, run1.id, {
        "metrics": {"total_lines": 1500, "code_lines": 1200},
        "summary": {"total_files": 25},
        "findings": [{"id": "F1"}, {"id": "F2"}]
    })
    mark_analysis_completed(db_session, run1.id)

    response = client.get("/api/repositories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    repo_item = data[0]
    assert repo_item["latest_analysis"] is not None
    latest = repo_item["latest_analysis"]
    assert latest["id"] == str(run1.id)
    assert latest["status"] == "completed"
    assert latest["analysis_type"] == "deterministic"
    assert latest["total_lines"] == 1500
    assert latest["code_lines"] == 1200
    assert latest["total_files"] == 25
    assert latest["findings_count"] == 2


def test_list_repositories_multi_user_isolation(db_session: Session, override_current_user: User):
    """Test user isolation: User A cannot see User B's repositories even with same URL."""
    other_user = User(
        id=uuid.uuid4(),
        github_user_id="2000002",
        github_login="other-user",
        name="Other User",
        email="other@devlens.local"
    )
    db_session.add(other_user)
    db_session.commit()

    meta = {"owner": "sharedorg", "name": "shared-repo"}
    repo_current = create_or_update_repository(
        db_session, meta, "https://github.com/sharedorg/shared-repo", user_id=override_current_user.id
    )
    repo_other = create_or_update_repository(
        db_session, meta, "https://github.com/sharedorg/shared-repo", user_id=other_user.id
    )

    # Authenticated as current user
    response = client.get("/api/repositories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(repo_current.id)
    assert str(repo_other.id) not in [r["id"] for r in data]


def test_delete_repository_success(db_session: Session, override_current_user: User):
    """Test owner can delete own repository."""
    meta = {"owner": "testorg", "name": "to-delete"}
    repo = create_or_update_repository(
        db_session, meta, "https://github.com/testorg/to-delete", user_id=override_current_user.id
    )

    response = client.delete(f"/api/repositories/{repo.id}")
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verify repository is gone
    check_response = client.get(f"/api/repositories/{repo.id}")
    assert check_response.status_code == 404


def test_delete_repository_cascades_analyses(db_session: Session, override_current_user: User):
    """Test deleting repository cascades and removes all associated analysis runs."""
    meta = {"owner": "testorg", "name": "cascade-test"}
    repo = create_or_update_repository(
        db_session, meta, "https://github.com/testorg/cascade-test", user_id=override_current_user.id
    )
    run1 = create_analysis_run(db_session, repo.id, AnalysisType.DETERMINISTIC.value)
    run2 = create_analysis_run(db_session, repo.id, AnalysisType.AI.value)

    # Delete repo
    response = client.delete(f"/api/repositories/{repo.id}")
    assert response.status_code == 200

    # Verify analysis runs are deleted
    run_check1 = client.get(f"/api/analyses/{run1.id}")
    assert run_check1.status_code == 404
    run_check2 = client.get(f"/api/analyses/{run2.id}")
    assert run_check2.status_code == 404


def test_delete_repository_non_owner_returns_404(db_session: Session, override_current_user: User):
    """Test non-owner deleting another user's repository receives 404 (tenant isolation)."""
    other_user = User(
        id=uuid.uuid4(),
        github_user_id="3000003",
        github_login="victim-user",
        name="Victim User",
        email="victim@devlens.local"
    )
    db_session.add(other_user)
    db_session.commit()

    meta = {"owner": "victimorg", "name": "victim-repo"}
    other_repo = create_or_update_repository(
        db_session, meta, "https://github.com/victimorg/victim-repo", user_id=other_user.id
    )

    # Current user attempts to delete other_user's repo
    response = client.delete(f"/api/repositories/{other_repo.id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    # Verify other_user's repository still exists in database
    existing = db_session.get(Repository, other_repo.id)
    assert existing is not None


def test_delete_repository_does_not_affect_other_user_same_url(
    db_session: Session, override_current_user: User
):
    """Test deleting own repository for a URL does not affect other user's repo for the same URL."""
    other_user = User(
        id=uuid.uuid4(),
        github_user_id="4000004",
        github_login="colleague-user",
        name="Colleague User",
        email="colleague@devlens.local"
    )
    db_session.add(other_user)
    db_session.commit()

    meta = {"owner": "sharedorg", "name": "dual-repo"}
    url = "https://github.com/sharedorg/dual-repo"

    my_repo = create_or_update_repository(db_session, meta, url, user_id=override_current_user.id)
    other_repo = create_or_update_repository(db_session, meta, url, user_id=other_user.id)

    # Delete my repo
    response = client.delete(f"/api/repositories/{my_repo.id}")
    assert response.status_code == 200

    # Other repo must still exist intact
    db_session.expire_all()
    other_check = db_session.get(Repository, other_repo.id)
    assert other_check is not None
    assert other_check.user_id == other_user.id


def test_delete_repository_nonexistent_returns_404():
    """Test deleting non-existent repository returns 404."""
    random_id = str(uuid.uuid4())
    response = client.delete(f"/api/repositories/{random_id}")
    assert response.status_code == 404


@pytest.mark.unauthenticated
def test_list_repositories_unauthenticated():
    """Test unauthenticated request to GET /api/repositories returns 401."""
    response = client.get("/api/repositories")
    assert response.status_code == 401


@pytest.mark.unauthenticated
def test_delete_repository_unauthenticated():
    """Test unauthenticated request to DELETE /api/repositories/{id} returns 401."""
    random_id = str(uuid.uuid4())
    response = client.delete(f"/api/repositories/{random_id}")
    assert response.status_code == 401
