from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import httpx
from app.services.github_service import (
    GitHubService,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubAPIError,
    is_placeholder_token,
)

# Enable asyncio in pytest (anyio is default installed)
pytestmark = pytest.mark.anyio


def test_is_placeholder_token():
    """
    Test placeholder token detection for various inputs.
    """
    # Placeholders / empty / none
    assert is_placeholder_token(None) is True
    assert is_placeholder_token("") is True
    assert is_placeholder_token("   ") is True
    assert is_placeholder_token("your_github_token_here") is True
    assert is_placeholder_token("YOUR_GITHUB_TOKEN_HERE") is True
    assert is_placeholder_token("your_token_here") is True
    assert is_placeholder_token("your_personal_access_token_here") is True
    assert is_placeholder_token("ghp_yourtokenhere") is True
    assert is_placeholder_token("ghp_xxxxxxxxxxxxxxxxxxxx") is True
    assert is_placeholder_token("<your_token_here>") is True
    assert is_placeholder_token("placeholder") is True
    assert is_placeholder_token("change_me") is True

    # Valid non-placeholder tokens
    assert is_placeholder_token("ghp_1234567890abcdefghijklmnopqrstuvwxyz") is False
    assert is_placeholder_token("github_pat_11ABCD_example_valid_token_string_99") is False
    assert is_placeholder_token("my_actual_github_access_token_abc123") is False


def test_github_service_token_initialization():
    """
    Test GitHubService header configuration with no token, placeholder token, and valid token.
    """
    # No token
    service_none = GitHubService(token="")
    assert "Authorization" not in service_none.headers
    assert service_none.token is None

    # Placeholder token
    service_placeholder = GitHubService(token="your_github_token_here")
    assert "Authorization" not in service_placeholder.headers
    assert service_placeholder.token is None
    assert service_placeholder.is_placeholder is True

    # Valid token
    service_valid = GitHubService(token="ghp_realtoken123456789")
    assert service_valid.headers.get("Authorization") == "Bearer ghp_realtoken123456789"
    assert service_valid.token == "ghp_realtoken123456789"
    assert service_valid.is_placeholder is False


async def test_get_repo_metadata_success():
    """
    Test successful metadata ingestion with expected payload fields and valid token header.
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

        service = GitHubService(token="ghp_valid_mock_token")
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
                "Authorization": "Bearer ghp_valid_mock_token"
            }
        )


async def test_get_repo_metadata_401_unauthorized():
    """
    Test that a 401 response raises GitHubAPIError with descriptive authentication error.
    """
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "message": "Bad credentials",
        "documentation_url": "https://docs.github.com/rest"
    }
    mock_response.text = '{"message": "Bad credentials"}'

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        service = GitHubService(token="ghp_invalid_token")
        with pytest.raises(GitHubAPIError) as exc_info:
            await service.get_repo_metadata("owner", "devlens")

        assert "401 Unauthorized" in str(exc_info.value)
        assert "Bad credentials" in str(exc_info.value)


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


async def test_get_repo_tree_401_unauthorized():
    """
    Test that a 401 response on tree retrieval raises GitHubAPIError.
    """
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.json.return_value = {"message": "Bad credentials"}
    mock_response.text = '{"message": "Bad credentials"}'

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        service = GitHubService()
        with pytest.raises(GitHubAPIError) as exc_info:
            await service.get_repo_tree("owner", "devlens", "main")
        assert "401 Unauthorized" in str(exc_info.value)


async def test_get_file_content_success():
    """
    Test successful file content retrieval.
    """
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.text = "print('Hello DevLens')"

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        service = GitHubService(token="ghp_test_token")
        content = await service.get_file_content("owner", "devlens", "main.py", "main")
        assert content == "print('Hello DevLens')"


async def test_get_file_content_401_unauthorized():
    """
    Test that a 401 response on file content retrieval raises GitHubAPIError.
    """
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.json.return_value = {"message": "Bad credentials"}
    mock_response.text = '{"message": "Bad credentials"}'

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        service = GitHubService()
        with pytest.raises(GitHubAPIError) as exc_info:
            await service.get_file_content("owner", "devlens", "main.py", "main")
        assert "401 Unauthorized" in str(exc_info.value)


async def test_network_connect_timeout_message():
    """
    Test that network connection errors provide clear message even if str(e) is empty.
    """
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectTimeout("")

        service = GitHubService()
        with pytest.raises(GitHubAPIError) as exc_info:
            await service.get_repo_metadata("owner", "devlens")
        assert "ConnectTimeout" in str(exc_info.value)
