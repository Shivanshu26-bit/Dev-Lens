import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.security import create_oauth_state
from app.models.user import User

client = TestClient(app)


def test_github_login_redirect():
    """Test GET /api/auth/github/login redirects to GitHub with valid state and client ID."""
    with patch.object(settings, "GITHUB_CLIENT_ID", "test_client_id"):
        response = client.get("/api/auth/github/login", follow_redirects=False)
        assert response.status_code == 302
        location = response.headers["location"]
        assert location.startswith("https://github.com/login/oauth/authorize")
        assert "client_id=test_client_id" in location
        assert "state=" in location
        assert "oauth_state" in response.cookies


def test_github_login_missing_client_id_error():
    """Test login endpoint returns 503 if GITHUB_CLIENT_ID is not configured."""
    with patch.object(settings, "GITHUB_CLIENT_ID", ""):
        response = client.get("/api/auth/github/login", follow_redirects=False)
        assert response.status_code == 503
        assert "not configured" in response.json()["detail"]


def test_github_callback_missing_params():
    """Test callback endpoint returns 400 when code or state is missing."""
    response = client.get("/api/auth/github/callback")
    assert response.status_code == 400
    assert "Missing authorization code or state" in response.json()["detail"]


def test_github_callback_invalid_state():
    """Test callback endpoint returns 400 when state is forged or invalid."""
    response = client.get("/api/auth/github/callback?code=mock_code&state=invalid_forged_state")
    assert response.status_code == 400
    assert "Invalid or expired OAuth state" in response.json()["detail"]


def test_github_callback_error_redirect():
    """Test callback endpoint redirects to frontend when user denies access on GitHub."""
    response = client.get("/api/auth/github/callback?error=access_denied", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == f"{settings.FRONTEND_URL}?auth_error=access_denied"


def test_github_callback_success(db_session):
    """Test full OAuth callback creates User and sets session cookie."""
    from unittest.mock import MagicMock
    valid_state = create_oauth_state()
    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {"access_token": "gho_mock_access_token_123"}

    mock_user_resp = MagicMock()
    mock_user_resp.status_code = 200
    mock_user_resp.json.return_value = {
        "id": 554433,
        "login": "new-octo-dev",
        "name": "Octo Developer",
        "email": "octo@example.com",
        "avatar_url": "https://avatars.githubusercontent.com/u/554433?v=4"
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch.object(settings, "GITHUB_CLIENT_ID", "mock_id"), \
         patch.object(settings, "GITHUB_CLIENT_SECRET", "mock_secret"):
        mock_post.return_value = mock_token_resp
        mock_get.return_value = mock_user_resp

        client.cookies.set("oauth_state", valid_state)
        response = client.get(
            f"/api/auth/github/callback?code=valid_code_123&state={valid_state}",
            follow_redirects=False
        )

        assert response.status_code == 302
        assert response.headers["location"] == settings.FRONTEND_URL
        assert settings.SESSION_COOKIE_NAME in response.cookies

        # Verify User was inserted into database
        user = db_session.query(User).filter(User.github_user_id == "554433").first()
        assert user is not None
        assert user.github_login == "new-octo-dev"
        assert user.name == "Octo Developer"
        assert user.email == "octo@example.com"
