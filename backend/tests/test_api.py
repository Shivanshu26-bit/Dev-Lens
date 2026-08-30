from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.github_service import GitHubNotFoundError, GitHubRateLimitError, GitHubAPIError

client = TestClient(app)

def test_analyze_repository_success():
    """
    Test that a valid GitHub repository URL returns 200 OK and structured data.
    """
    mock_metadata = {
        "owner": "owner-name",
        "name": "devlens-core",
        "full_name": "owner-name/devlens-core",
        "description": "Core analyzer service",
        "default_branch": "main",
        "visibility": "public",
        "language": "Python",
        "stars": 50,
        "forks": 5,
        "open_issues": 1,
        "url": "https://github.com/owner-name/devlens-core",
        "created_at": "2026-08-24T12:00:00Z",
        "updated_at": "2026-08-24T12:00:00Z"
    }
    
    mock_tree = [
        {"path": "app", "type": "directory"},
        {"path": "README.md", "type": "file"}
    ]

    with patch("app.api.repositories.GitHubService.get_repo_metadata", new_callable=AsyncMock) as mock_get_metadata, \
         patch("app.api.repositories.GitHubService.get_repo_tree", new_callable=AsyncMock) as mock_get_tree:
         
        mock_get_metadata.return_value = mock_metadata
        mock_get_tree.return_value = mock_tree
        
        response = client.post(
            "/api/repositories/analyze",
            json={"url": "https://github.com/owner-name/devlens-core"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify repository metadata
        assert data["repository"]["name"] == "devlens-core"
        assert data["repository"]["stars"] == 50
        assert data["repository"]["language"] == "Python"
        assert data["repository"]["default_branch"] == "main"
        
        # Verify tree mappings
        assert len(data["tree"]) == 2
        assert data["tree"][0] == {"path": "app", "type": "directory"}
        assert data["tree"][1] == {"path": "README.md", "type": "file"}

def test_analyze_repository_invalid_url():
    """
    Test that an invalid GitHub URL structure returns 400 Bad Request.
    """
    response = client.post(
        "/api/repositories/analyze",
        json={"url": "https://github.com/owner/repo/pull/15"}
    )
    assert response.status_code == 400
    assert "Invalid GitHub" in response.json()["detail"]

def test_analyze_repository_not_found():
    """
    Test that a repository 404 maps to HTTP 404.
    """
    with patch("app.api.repositories.GitHubService.get_repo_metadata", new_callable=AsyncMock) as mock_get_metadata:
        mock_get_metadata.side_effect = GitHubNotFoundError("Repository not found")
        
        response = client.post(
            "/api/repositories/analyze",
            json={"url": "https://github.com/owner/not-found"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

def test_analyze_repository_rate_limit():
    """
    Test that a GitHub API rate limit exception maps to HTTP 429.
    """
    with patch("app.api.repositories.GitHubService.get_repo_metadata", new_callable=AsyncMock) as mock_get_metadata:
        mock_get_metadata.side_effect = GitHubRateLimitError("Rate limit exceeded")
        
        response = client.post(
            "/api/repositories/analyze",
            json={"url": "https://github.com/owner/limited"}
        )
        
        assert response.status_code == 429
        assert "rate limit exceeded" in response.json()["detail"].lower()

def test_analyze_repository_api_error():
    """
    Test that a general GitHub API error maps to HTTP 502 Bad Gateway.
    """
    with patch("app.api.repositories.GitHubService.get_repo_metadata", new_callable=AsyncMock) as mock_get_metadata:
        mock_get_metadata.side_effect = GitHubAPIError("Gateway connection timeout")
        
        response = client.post(
            "/api/repositories/analyze",
            json={"url": "https://github.com/owner/failed-api"}
        )
        
        assert response.status_code == 502
        assert "gateway" in response.text.lower() or "timeout" in response.text.lower()
