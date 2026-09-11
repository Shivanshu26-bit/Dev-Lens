from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db

client = TestClient(app)


def test_health_check_database_connected():
    """
    Test that GET /health returns HTTP 200 and 'connected' when the database is reachable.
    """
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["project"] == "DevLens"
    assert data["database"] == "connected"
    assert "features" in data
    assert data["features"]["database_integrated"] is True


def test_health_check_database_disconnected():
    """
    Test that GET /health returns HTTP 503 and 'disconnected' when the database is unreachable.
    """
    mock_failing_db = MagicMock()
    mock_failing_db.execute.side_effect = Exception("Database connection refused")

    def _failing_get_db():
        yield mock_failing_db

    app.dependency_overrides[get_db] = _failing_get_db
    try:
        response = client.get("/health")
        assert response.status_code == 503

        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["project"] == "DevLens"
        assert data["database"] == "disconnected"
        assert data["features"]["database_integrated"] is False
    finally:
        app.dependency_overrides.pop(get_db, None)
