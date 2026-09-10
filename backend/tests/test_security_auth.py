import uuid
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import settings
from app.core.security import create_oauth_state, verify_oauth_state
from app.models.user import User
from app.services.session_service import create_user_session

client = TestClient(app)


@pytest.mark.skip_auth_mock
def test_user_endpoints_do_not_leak_secrets(db_session: Session):
    """
    Verify that user response schemas and endpoints never expose sensitive tokens,
    credentials, or internal secrets.
    """
    client.cookies.clear()
    user = User(
        id=uuid.uuid4(),
        github_user_id="secret-check-user",
        github_login="secure-dev",
        name="Secure Dev",
        email="secure@example.com",
        avatar_url="https://avatars.githubusercontent.com/u/9999?v=4"
    )
    db_session.add(user)
    db_session.commit()

    token, _ = create_user_session(db_session, user.id)
    client.cookies.set(settings.SESSION_COOKIE_NAME, token)

    response = client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()

    # Verify expected public fields
    assert data["id"] == str(user.id)
    assert data["github_login"] == "secure-dev"
    assert data["name"] == "Secure Dev"
    assert data["email"] == "secure@example.com"
    assert data["avatar_url"] == "https://avatars.githubusercontent.com/u/9999?v=4"

    # Assert NO secret leaks
    forbidden_keys = [
        "access_token",
        "github_token",
        "token",
        "client_secret",
        "secret",
        "password",
        "hashed_password",
        "secret_key"
    ]
    for key in forbidden_keys:
        assert key not in data, f"Sensitive key '{key}' was leaked in /api/auth/me response"


@pytest.mark.skip_auth_mock
def test_oauth_login_sets_secure_state_cookie():
    """
    Verify that initiating OAuth login sets an HttpOnly cookie with the CSRF state.
    """
    with patch.object(settings, "GITHUB_CLIENT_ID", "test_client"):
        response = client.get("/api/auth/github/login", follow_redirects=False)
        assert response.status_code == 302
        assert "oauth_state" in response.cookies

        # Inspect Set-Cookie header flags
        cookie_headers = [h[1].decode() for h in response.headers.raw if h[0].lower() == b"set-cookie"]
        state_cookie = next((h for h in cookie_headers if "oauth_state=" in h), None)
        assert state_cookie is not None
        assert "HttpOnly" in state_cookie
        assert "samesite=lax" in state_cookie.lower()


@pytest.mark.skip_auth_mock
def test_oauth_state_tampering_rejected():
    """
    Verify that a forged or altered OAuth state parameter is rejected during callback.
    """
    valid_state = create_oauth_state()
    # Set legitimate cookie
    client.cookies.set("oauth_state", valid_state)

    # But query parameter provides tampered state
    tampered_state = valid_state + "tampered"
    response = client.get(f"/api/auth/github/callback?code=mock_code&state={tampered_state}")
    assert response.status_code == 400
    assert "Invalid or expired OAuth state" in response.json()["detail"]


@pytest.mark.skip_auth_mock
def test_oauth_state_cross_site_mismatch_rejected():
    """
    Verify that if the cookie does not match the callback state, the request is rejected.
    """
    client.cookies.clear()
    state_cookie = create_oauth_state()
    state_param = create_oauth_state()

    client.cookies.set("oauth_state", state_cookie)
    response = client.get(f"/api/auth/github/callback?code=mock_code&state={state_param}")
    assert response.status_code == 400
    assert "OAuth state mismatch" in response.json()["detail"]


@pytest.mark.skip_auth_mock
def test_oauth_state_missing_cookie_rejected():
    """
    Verify that if the oauth_state cookie is missing entirely, the request is rejected with 400.
    Prevents OAuth Login CSRF bypasses.
    """
    client.cookies.clear()
    valid_state = create_oauth_state()

    response = client.get(f"/api/auth/github/callback?code=mock_code&state={valid_state}")
    assert response.status_code == 400
    assert "OAuth state mismatch or missing state cookie" in response.json()["detail"]


@pytest.mark.skip_auth_mock
def test_session_cookie_flags_on_successful_login(db_session: Session):
    """
    Verify that the session cookie issued upon successful OAuth callback has HttpOnly,
    SameSite=Lax, and Path=/.
    """
    from unittest.mock import MagicMock
    client.cookies.clear()
    valid_state = create_oauth_state()
    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {"access_token": "gho_test_token"}

    mock_user_resp = MagicMock()
    mock_user_resp.status_code = 200
    mock_user_resp.json.return_value = {
        "id": 887766,
        "login": "cookie-test-user",
        "name": "Cookie Tester",
        "email": "cookie@example.com",
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch.object(settings, "GITHUB_CLIENT_ID", "mock_id"), \
         patch.object(settings, "GITHUB_CLIENT_SECRET", "mock_secret"):
        mock_post.return_value = mock_token_resp
        mock_get.return_value = mock_user_resp

        client.cookies.set("oauth_state", valid_state)
        response = client.get(
            f"/api/auth/github/callback?code=code_abc&state={valid_state}",
            follow_redirects=False
        )

        assert response.status_code == 302
        cookie_headers = [h[1].decode() for h in response.headers.raw if h[0].lower() == b"set-cookie"]
        session_cookie_header = next(
            (h for h in cookie_headers if f"{settings.SESSION_COOKIE_NAME}=" in h),
            None
        )
        assert session_cookie_header is not None
        assert "HttpOnly" in session_cookie_header
        assert "samesite=lax" in session_cookie_header.lower()
        assert "Path=/" in session_cookie_header


@pytest.mark.skip_auth_mock
def test_unauthenticated_protected_endpoints_return_401():
    """
    Verify all key protected endpoints return 401 Unauthorized when requested
    without credentials.
    """
    client.cookies.clear()
    endpoints = [
        ("GET", "/api/auth/me"),
        ("POST", "/api/repositories/analyze"),
        ("POST", "/api/repositories/analyze/ai"),
        ("GET", f"/api/repositories/{uuid.uuid4()}"),
        ("GET", f"/api/repositories/{uuid.uuid4()}/analyses"),
        ("GET", f"/api/repositories/{uuid.uuid4()}/trends"),
        ("GET", f"/api/analyses/{uuid.uuid4()}"),
    ]

    for method, path in endpoints:
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path, json={"url": "https://github.com/owner/repo"})
        assert resp.status_code == 401, f"Expected 401 for {method} {path}, got {resp.status_code}"
        assert "Not authenticated" in resp.json()["detail"]


def test_production_secret_key_guardrail():
    """
    Verify that Pydantic rejects the default insecure SECRET_KEY when
    SESSION_COOKIE_SECURE is True (production mode), but allows custom keys
    or development mode.
    """
    from pydantic import ValidationError
    from app.core.config import Settings

    # 1. Production mode with default insecure key must fail validation
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            SESSION_COOKIE_SECURE=True,
            SECRET_KEY="devlens-insecure-secret-key-change-in-production-32b"
        )
    assert "Insecure default SECRET_KEY cannot be used in production" in str(exc_info.value)

    # 2. Production mode with strong custom key must succeed
    prod_settings = Settings(
        SESSION_COOKIE_SECURE=True,
        SECRET_KEY="a-very-strong-production-cryptographic-secret-key-12345"
    )
    assert prod_settings.SESSION_COOKIE_SECURE is True
    assert prod_settings.SECRET_KEY == "a-very-strong-production-cryptographic-secret-key-12345"

    # 3. Development mode (SESSION_COOKIE_SECURE=False) allows the default key
    dev_settings = Settings(
        SESSION_COOKIE_SECURE=False,
        SECRET_KEY="devlens-insecure-secret-key-change-in-production-32b"
    )
    assert dev_settings.SESSION_COOKIE_SECURE is False
