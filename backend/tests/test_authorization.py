import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import settings
from app.models.user import User
from app.models.analysis import AnalysisType
from app.services.session_service import create_user_session
from app.services.repository_persistence import create_or_update_repository
from app.services.analysis_persistence import create_analysis_run

client = TestClient(app)


@pytest.fixture
def user_a(db_session: Session) -> User:
    """Create User A."""
    user = User(
        id=uuid.uuid4(),
        github_user_id="github-user-a",
        github_login="user-a",
        name="User Alpha",
        email="alpha@example.com"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_b(db_session: Session) -> User:
    """Create User B."""
    user = User(
        id=uuid.uuid4(),
        github_user_id="github-user-b",
        github_login="user-b",
        name="User Beta",
        email="beta@example.com"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.mark.skip_auth_mock
def test_cross_user_repository_access_returns_404(db_session: Session, user_a: User, user_b: User):
    """
    Verify that User B cannot access User A's repository.
    Returns 404 (not 403) to prevent ID enumeration.
    """
    client.cookies.clear()
    repo_a = create_or_update_repository(
        db_session,
        {"owner": "user-a", "name": "secret-project", "stars": 10},
        "https://github.com/user-a/secret-project",
        user_id=user_a.id
    )

    # User B logs in via database session
    raw_token_b, _ = create_user_session(db_session, user_b.id)
    client.cookies.set(settings.SESSION_COOKIE_NAME, raw_token_b)

    response = client.get(f"/api/repositories/{repo_a.id}")
    assert response.status_code == 404
    assert f"Repository '{repo_a.id}' not found" in response.json()["detail"]


@pytest.mark.skip_auth_mock
def test_cross_user_repository_analyses_access_returns_404(db_session: Session, user_a: User, user_b: User):
    """
    Verify that User B cannot list analysis runs for User A's repository.
    Returns 404 to prevent resource existence leaking.
    """
    client.cookies.clear()
    repo_a = create_or_update_repository(
        db_session,
        {"owner": "user-a", "name": "project-analysis", "stars": 5},
        "https://github.com/user-a/project-analysis",
        user_id=user_a.id
    )
    create_analysis_run(db_session, repo_a.id, AnalysisType.DETERMINISTIC.value)

    # User B logs in
    raw_token_b, _ = create_user_session(db_session, user_b.id)
    client.cookies.set(settings.SESSION_COOKIE_NAME, raw_token_b)

    response = client.get(f"/api/repositories/{repo_a.id}/analyses")
    assert response.status_code == 404
    assert f"Repository '{repo_a.id}' not found" in response.json()["detail"]


@pytest.mark.skip_auth_mock
def test_cross_user_analysis_by_id_access_returns_404(db_session: Session, user_a: User, user_b: User):
    """
    Verify that User B cannot fetch an analysis run directly by ID if owned by User A.
    Returns 404 to prevent ID enumeration.
    """
    client.cookies.clear()
    repo_a = create_or_update_repository(
        db_session,
        {"owner": "user-a", "name": "repo-alpha", "stars": 12},
        "https://github.com/user-a/repo-alpha",
        user_id=user_a.id
    )
    run_a = create_analysis_run(db_session, repo_a.id, AnalysisType.AI.value)

    # User B logs in
    raw_token_b, _ = create_user_session(db_session, user_b.id)
    client.cookies.set(settings.SESSION_COOKIE_NAME, raw_token_b)

    response = client.get(f"/api/analyses/{run_a.id}")
    assert response.status_code == 404
    assert f"Analysis run '{run_a.id}' not found" in response.json()["detail"]


@pytest.mark.skip_auth_mock
def test_null_user_id_repository_inaccessible_to_arbitrary_authenticated_user(db_session: Session, user_a: User):
    """
    REGRESSION TEST: Verify that a legacy repository with user_id=NULL
    cannot be accessed by an arbitrary authenticated user.
    Ensures NULL user_id does NOT grant open access to anyone.
    """
    client.cookies.clear()
    # Create legacy repository with explicit user_id=None
    legacy_repo = create_or_update_repository(
        db_session,
        {"owner": "legacy-org", "name": "legacy-repo", "stars": 99},
        "https://github.com/legacy-org/legacy-repo",
        user_id=None
    )
    assert legacy_repo.user_id is None

    legacy_run = create_analysis_run(db_session, legacy_repo.id, AnalysisType.DETERMINISTIC.value)

    # Authenticate as User A
    raw_token_a, _ = create_user_session(db_session, user_a.id)
    client.cookies.set(settings.SESSION_COOKIE_NAME, raw_token_a)

    # 1. Attempt to fetch repo by ID
    resp_repo = client.get(f"/api/repositories/{legacy_repo.id}")
    assert resp_repo.status_code == 404
    assert f"Repository '{legacy_repo.id}' not found" in resp_repo.json()["detail"]

    # 2. Attempt to list analyses for legacy repo
    resp_analyses = client.get(f"/api/repositories/{legacy_repo.id}/analyses")
    assert resp_analyses.status_code == 404
    assert f"Repository '{legacy_repo.id}' not found" in resp_analyses.json()["detail"]

    # 3. Attempt to fetch analysis run by ID
    resp_run = client.get(f"/api/analyses/{legacy_run.id}")
    assert resp_run.status_code == 404
    assert f"Analysis run '{legacy_run.id}' not found" in resp_run.json()["detail"]


@pytest.mark.skip_auth_mock
def test_multi_user_same_url_independence(db_session: Session, user_a: User, user_b: User):
    """
    Verify that User A and User B can both persist the same GitHub URL independently
    without unique constraint collision or cross-tenant data leakage.
    """
    client.cookies.clear()
    url = "https://github.com/popular/shared-repo"

    # User A analyzes and creates repo
    repo_a = create_or_update_repository(
        db_session,
        {"owner": "popular", "name": "shared-repo", "stars": 5000},
        url,
        user_id=user_a.id
    )
    run_a = create_analysis_run(db_session, repo_a.id, AnalysisType.DETERMINISTIC.value)

    # User B analyzes and creates repo with same URL
    repo_b = create_or_update_repository(
        db_session,
        {"owner": "popular", "name": "shared-repo", "stars": 5000},
        url,
        user_id=user_b.id
    )
    run_b = create_analysis_run(db_session, repo_b.id, AnalysisType.AI.value)

    # They should have distinct IDs and user_ids
    assert repo_a.id != repo_b.id
    assert repo_a.user_id == user_a.id
    assert repo_b.user_id == user_b.id

    # User A accesses own repo and analyses
    token_a, _ = create_user_session(db_session, user_a.id)
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_a)

    resp_a = client.get(f"/api/repositories/{repo_a.id}")
    assert resp_a.status_code == 200
    assert resp_a.json()["id"] == str(repo_a.id)

    runs_a = client.get(f"/api/repositories/{repo_a.id}/analyses").json()
    assert len(runs_a) == 1
    assert runs_a[0]["id"] == str(run_a.id)

    # User B accesses own repo and analyses
    token_b, _ = create_user_session(db_session, user_b.id)
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_b)

    resp_b = client.get(f"/api/repositories/{repo_b.id}")
    assert resp_b.status_code == 200
    assert resp_b.json()["id"] == str(repo_b.id)

    runs_b = client.get(f"/api/repositories/{repo_b.id}/analyses").json()
    assert len(runs_b) == 1
    assert runs_b[0]["id"] == str(run_b.id)
