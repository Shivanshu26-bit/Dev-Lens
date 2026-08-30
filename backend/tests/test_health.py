from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """
    Test that GET /health returns HTTP 200 and the expected JSON body.
    """
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "ok"
    assert data["project"] == "DevLens"
    assert "features" in data
    assert data["features"]["database_integrated"] is False
    assert data["features"]["ai_analysis_integrated"] is False
