import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import settings
from app.core.security import hash_session_token
from app.models.user import User
from app.models.user_session import UserSession
from app.services.session_service import create_user_session

client = TestClient(app)


@pytest.fixture
def session_user(db_session: Session) -> User:
    """Creates a test user for session tests."""
    user = User(
        id=uuid.uuid4(),
        github_user_id="session-user-1",
        github_login="session-dev",
        name="Session Dev",
        email="session@example.com"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.mark.skip_auth_mock
def test_unauthenticated_me_endpoint_rejected():
    """Test GET /api/auth/me returns 401 when no session cookie is supplied."""
    client.cookies.clear()
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.skip_auth_mock
def test_authenticated_me_endpoint_succeeds(db_session: Session, session_user: User):
    """Test GET /api/auth/me returns 200 and User profile when valid session cookie is provided."""
    client.cookies.clear()
    raw_token, session_record = create_user_session(db_session, session_user.id)
    client.cookies.set(settings.SESSION_COOKIE_NAME, raw_token)

    response = client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["github_login"] == "session-dev"
    assert data["email"] == "session@example.com"
    assert "access_token" not in data
    assert "secret" not in data


@pytest.mark.skip_auth_mock
def test_revoked_session_cookie_rejected(db_session: Session, session_user: User):
    """
    Test that a session marked is_revoked=True in the database is rejected with 401.
    Demonstrates server-side session revocation.
    """
    client.cookies.clear()
    raw_token, session_record = create_user_session(db_session, session_user.id)

    # Revoke the session in PostgreSQL
    session_record.is_revoked = True
    db_session.commit()

    client.cookies.set(settings.SESSION_COOKIE_NAME, raw_token)
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "Invalid or expired session" in response.json()["detail"]


@pytest.mark.skip_auth_mock
def test_expired_session_cookie_rejected(db_session: Session, session_user: User):
    """Test that a session with expires_at in the past is rejected with 401."""
    client.cookies.clear()
    raw_token, session_record = create_user_session(db_session, session_user.id)

    # Set expires_at in the past
    session_record.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    client.cookies.set(settings.SESSION_COOKIE_NAME, raw_token)
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "Invalid or expired session" in response.json()["detail"]


@pytest.mark.skip_auth_mock
def test_tampered_unknown_session_cookie_rejected():
    """Test that an unknown or forged session cookie is rejected with 401."""
    client.cookies.clear()
    client.cookies.set(settings.SESSION_COOKIE_NAME, "forged_random_unregistered_token_12345")
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "Invalid or expired session" in response.json()["detail"]


@pytest.mark.skip_auth_mock
def test_logout_endpoint_revokes_session_in_database(db_session: Session, session_user: User):
    """
    Test POST /api/auth/logout:
    1. Revokes the session record in the database (is_revoked = True).
    2. Clears the session cookie in response headers.
    3. Prevents any future authentication using that previously issued token.
    """
    client.cookies.clear()
    raw_token, session_record = create_user_session(db_session, session_user.id)
    token_hash = hash_session_token(raw_token)

    # Verify initially active
    assert session_record.is_revoked is False

    client.cookies.set(settings.SESSION_COOKIE_NAME, raw_token)
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"

    # 1. Verify session is revoked in database
    db_session.refresh(session_record)
    assert session_record.is_revoked is True

    # 2. Verify Set-Cookie header cleared the cookie
    cookie_headers = [h for h in response.headers.raw if h[0].lower() == b"set-cookie"]
    assert any(settings.SESSION_COOKIE_NAME.encode() in h[1] for h in cookie_headers)

    # 3. Attempt to reuse the same raw_token after logout
    client.cookies.set(settings.SESSION_COOKIE_NAME, raw_token)
    retry_resp = client.get("/api/auth/me")
    assert retry_resp.status_code == 401
    assert "Invalid or expired session" in retry_resp.json()["detail"]
