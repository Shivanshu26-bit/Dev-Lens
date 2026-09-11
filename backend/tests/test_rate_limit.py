import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.rate_limit import (
    limiter,
    get_client_ip,
    get_rate_limit_key,
    get_storage_uri,
)


@pytest.fixture
def client():
    """TestClient fixture for executing HTTP requests against app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Ensure rate limiter storage is reset before and after each test."""
    limiter.reset()
    yield
    limiter.reset()


def test_storage_uri_resolution(monkeypatch):
    """Verify storage URI resolution logic between REDIS_URL, RATE_LIMIT_STORAGE_URL, and memory."""
    # Default is memory
    monkeypatch.setattr(settings, "RATE_LIMIT_STORAGE_URL", "")
    monkeypatch.setattr(settings, "REDIS_URL", "")
    assert get_storage_uri() == "memory://"

    # REDIS_URL is used when set
    monkeypatch.setattr(settings, "REDIS_URL", "redis://redis.render.internal:6379/0")
    assert get_storage_uri() == "redis://redis.render.internal:6379/0"

    # RATE_LIMIT_STORAGE_URL takes highest precedence
    monkeypatch.setattr(settings, "RATE_LIMIT_STORAGE_URL", "redis://custom-redis:6379/1")
    assert get_storage_uri() == "redis://custom-redis:6379/1"


def test_get_client_ip_with_forwarded_for():
    """Verify get_client_ip prioritizes client IP from X-Forwarded-For behind reverse proxy."""
    mock_request = MagicMock()
    mock_request.headers = {"x-forwarded-for": "203.0.113.195, 10.0.0.1"}
    mock_request.client.host = "10.0.0.1"
    assert get_client_ip(mock_request) == "203.0.113.195"

    # Single IP in header
    mock_request.headers = {"x-forwarded-for": "198.51.100.42"}
    assert get_client_ip(mock_request) == "198.51.100.42"

    # Fallback to direct client host
    mock_request.headers = {}
    mock_request.client.host = "192.168.1.50"
    assert get_client_ip(mock_request) == "192.168.1.50"


def test_get_rate_limit_key_session_vs_ip():
    """Verify get_rate_limit_key keys on user session cookie when present, or client IP."""
    mock_request = MagicMock()
    mock_request.cookies = {settings.SESSION_COOKIE_NAME: "test-valid-session-token-123"}
    mock_request.headers = {}
    assert get_rate_limit_key(mock_request) == "sess:test-valid-session-token-123"

    # Unauthenticated client
    mock_request.cookies = {}
    mock_request.headers = {"x-forwarded-for": "198.51.100.1"}
    assert get_rate_limit_key(mock_request) == "ip:198.51.100.1"


def test_github_login_rate_limiting(client: TestClient, monkeypatch):
    """Verify GET /api/auth/github/login allows requests up to limit and returns HTTP 429 when exceeded."""
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_LOGIN", "3/minute")
    monkeypatch.setattr(settings, "GITHUB_CLIENT_ID", "test_client_id")
    limiter.reset()

    # Requests 1, 2, 3 should succeed (HTTP 302 redirect to GitHub OAuth)
    for _ in range(3):
        res = client.get("/api/auth/github/login", follow_redirects=False)
        assert res.status_code == 302
        assert "github.com/login/oauth/authorize" in res.headers["location"]

    # Request 4 should be blocked with 429
    blocked = client.get("/api/auth/github/login", follow_redirects=False)
    assert blocked.status_code == 429
    assert "Rate limit exceeded" in blocked.json()["detail"]
    assert "Retry-After" in blocked.headers


def test_analyze_repository_rate_limiting(client: TestClient, monkeypatch):
    """Verify POST /api/repositories/analyze allows requests up to limit and rejects with HTTP 429."""
    monkeypatch.setattr(settings, "RATE_LIMIT_ANALYZE", "2/minute")
    limiter.reset()

    mock_metadata = {
        "owner": "testorg",
        "name": "testrepo",
        "full_name": "testorg/testrepo",
        "description": "Test",
        "default_branch": "main",
        "language": "Python",
        "stars": 10,
        "forks": 2,
        "open_issues": 0,
        "url": "https://github.com/testorg/testrepo",
    }
    mock_tree = [{"path": "main.py", "type": "file"}]

    with patch("app.api.repositories.GitHubService") as mock_gh_cls:
        mock_gh = MagicMock()
        mock_gh.get_repo_metadata = AsyncMock(return_value=mock_metadata)
        mock_gh.get_repo_tree = AsyncMock(return_value=mock_tree)
        mock_gh_cls.return_value = mock_gh

        # First 2 requests succeed (200 OK)
        for _ in range(2):
            res = client.post(
                "/api/repositories/analyze",
                json={"url": "https://github.com/testorg/testrepo"}
            )
            assert res.status_code == 200
            assert res.json()["repository"]["name"] == "testrepo"

        # 3rd request hits 429 Too Many Requests
        blocked = client.post(
            "/api/repositories/analyze",
            json={"url": "https://github.com/testorg/testrepo"}
        )
        assert blocked.status_code == 429
        assert "Rate limit exceeded" in blocked.json()["detail"]
        assert "Retry-After" in blocked.headers


def test_analyze_ai_rate_limiting(client: TestClient, monkeypatch):
    """Verify POST /api/repositories/analyze/ai allows requests up to limit and rejects with HTTP 429."""
    monkeypatch.setattr(settings, "RATE_LIMIT_AI_ANALYZE", "2/minute")
    limiter.reset()

    mock_metadata = {
        "owner": "testorg",
        "name": "airepo",
        "full_name": "testorg/airepo",
        "description": "AI Test",
        "default_branch": "main",
        "language": "Python",
        "stars": 5,
        "forks": 1,
        "open_issues": 0,
        "url": "https://github.com/testorg/airepo",
    }
    from tests.test_api_ai import get_mock_deterministic_report, get_mock_ai_report

    mock_tree = [{"path": "main.py", "type": "file"}]
    mock_det_report = get_mock_deterministic_report()
    mock_ai_report = get_mock_ai_report()

    with patch("app.api.repositories.GitHubService") as mock_gh_cls, \
         patch("app.api.repositories.run_repo_analysis", new_callable=AsyncMock) as mock_run_repo, \
         patch("app.api.repositories.EvidenceSelector") as mock_sel_cls, \
         patch("app.api.repositories.AIService") as mock_ai_cls:

        mock_gh = MagicMock()
        mock_gh.get_repo_metadata = AsyncMock(return_value=mock_metadata)
        mock_gh.get_repo_tree = AsyncMock(return_value=mock_tree)
        mock_gh_cls.return_value = mock_gh

        mock_run_repo.return_value = mock_det_report

        mock_sel = MagicMock()
        mock_sel.select_evidence = AsyncMock(return_value=MagicMock())
        mock_sel_cls.return_value = mock_sel

        mock_ai = MagicMock()
        mock_ai.analyze_repository = AsyncMock(return_value=mock_ai_report)
        mock_ai_cls.return_value = mock_ai

        # First 2 requests succeed
        for _ in range(2):
            res = client.post(
                "/api/repositories/analyze/ai",
                json={"url": "https://github.com/testorg/airepo"}
            )
            assert res.status_code == 200
            assert res.json()["repository"]["name"] == "devlens"

        # 3rd request rejected with HTTP 429
        blocked = client.post(
            "/api/repositories/analyze/ai",
            json={"url": "https://github.com/testorg/airepo"}
        )
        assert blocked.status_code == 429
        assert "Rate limit exceeded" in blocked.json()["detail"]
        assert "Retry-After" in blocked.headers


@pytest.mark.skip_auth_mock
def test_unauthenticated_request_still_returns_401(client: TestClient):
    """Verify that unauthenticated requests to rate-limited endpoints preserve 401 checks."""
    res = client.post(
        "/api/repositories/analyze",
        json={"url": "https://github.com/testorg/testrepo"}
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Not authenticated"


def test_rate_limit_disabled_flag(client: TestClient, monkeypatch):
    """Verify that when RATE_LIMIT_ENABLED is False, limits are bypassed."""
    monkeypatch.setattr(limiter, "enabled", False)
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_LOGIN", "1/minute")
    monkeypatch.setattr(settings, "GITHUB_CLIENT_ID", "test_client_id")
    limiter.reset()

    # 3 requests succeed without hitting 429 because limiter is disabled
    for _ in range(3):
        res = client.get("/api/auth/github/login", follow_redirects=False)
        assert res.status_code == 302
