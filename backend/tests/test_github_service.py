from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import httpx
from app.services.github_service import (
    GitHubService,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubAPIError
)

# Enable asyncio in pytest (anyio is default installed)
pytestmark = pytest.mark.anyio

async def test_get_repo_metadata_success():
    """
    Test successful metadata ingestion with expected payload fields.
    """
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "name": "devlens",
        "full_name": "owner/devlens",
        "description": "Repo description text",
        "stargazers_count": 100,
        "forks_count": 25,
        "open_issues_count": 10,
        "html_url": "https://github.com/owner/devlens",
        "default_branch": "main",
        "visibility": "public",
        "language": "TypeScript",
        "owner": {"login": "owner"},
        "created_at": "2026-08-24T12:00:00Z",
        "updated_at": "2026-08-24T12:00:00Z"
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        service = GitHubService(token="mock_token")
        metadata = await service.get_repo_metadata("owner", "devlens")
        
        assert metadata["name"] == "devlens"
        assert metadata["stars"] == 100
        assert metadata["forks"] == 25
        assert metadata["open_issues"] == 10
        assert metadata["language"] == "TypeScript"
        assert metadata["default_branch"] == "main"
        
        mock_get.assert_called_once_with(
            "https://api.github.com/repos/owner/devlens",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "DevLens-App",
                "Authorization": "Bearer mock_token"
            }
        )

async def test_get_repo_metadata_not_found():
    """
    Test that a 404 response raises GitHubNotFoundError.
    """
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.text = "Not Found"

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        service = GitHubService()
        with pytest.raises(GitHubNotFoundError) as exc_info:
            await service.get_repo_metadata("owner", "not-found-repo")
        assert "not found" in str(exc_info.value).lower()

async def test_get_repo_metadata_rate_limit():
    """
    Test that a 403 response with x-ratelimit-remaining=0 raises GitHubRateLimitError.
    """
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 403
    mock_response.headers = {"x-ratelimit-remaining": "0"}
    mock_response.text = "API rate limit exceeded"

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        service = GitHubService()
        with pytest.raises(GitHubRateLimitError) as exc_info:
            await service.get_repo_metadata("owner", "devlens")
        assert "rate limit exceeded" in str(exc_info.value).lower()

async def test_get_repo_tree_success():
    """
    Test that the file tree is loaded, formatted, and capped successfully.
    """
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "tree": [
            {"path": "backend", "type": "tree"},
            {"path": "backend/app", "type": "tree"},
            {"path": "README.md", "type": "blob"},
            {"path": "submodule", "type": "commit"}  # Should be skipped
        ]
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        service = GitHubService()
        tree = await service.get_repo_tree("owner", "devlens", "main")
        
        assert len(tree) == 3
        assert tree[0] == {"path": "backend", "type": "directory"}
        assert tree[1] == {"path": "backend/app", "type": "directory"}
        assert tree[2] == {"path": "README.md", "type": "file"}
