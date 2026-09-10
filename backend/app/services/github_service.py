import logging
from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

# Known placeholder patterns for GITHUB_TOKEN in configuration templates
PLACEHOLDER_TOKEN_PATTERNS = {
    "your_github_token_here",
    "your_github_token",
    "your_token_here",
    "your_token",
    "your_personal_access_token_here",
    "your_personal_access_token",
    "ghp_yourtokenhere",
    "ghp_xxxxxxxxxxxxxxxxxxxx",
    "placeholder",
    "change_me",
    "changeme",
    "token_here",
}

def is_placeholder_token(token: Optional[str]) -> bool:
    """
    Determines if a given GitHub token string is missing, empty, or a known placeholder value.
    """
    if not token or not isinstance(token, str):
        return True
    cleaned = token.strip()
    if not cleaned:
        return True
    lowered = cleaned.lower()
    if lowered in PLACEHOLDER_TOKEN_PATTERNS:
        return True
    if (
        lowered.startswith("your_")
        or lowered.startswith("your-")
        or (lowered.startswith("<") and lowered.endswith(">"))
        or (lowered.startswith("[") and lowered.endswith("]"))
        or (lowered.startswith("{") and lowered.endswith("}"))
        or lowered.endswith("_here")
        or lowered.endswith("-here")
        or lowered == "placeholder"
        or lowered == "example_token"
    ):
        return True
    return False


def _extract_github_error_message(response: httpx.Response) -> str:
    """
    Safely extracts an error message or status summary from a GitHub API response
    without exposing any token or credential data.
    """
    try:
        data = response.json()
        if isinstance(data, dict) and "message" in data:
            return str(data["message"])
    except Exception:
        pass
    if response.text:
        return response.text[:200].strip()
    return f"HTTP {response.status_code}"


class GitHubServiceError(Exception):
    """Base exception class for all GitHub service errors."""
    pass

class GitHubNotFoundError(GitHubServiceError):
    """Exception raised when the repository is not found or is private."""
    pass

class GitHubRateLimitError(GitHubServiceError):
    """Exception raised when the GitHub API rate limit is reached."""
    pass

class GitHubAPIError(GitHubServiceError):
    """Exception raised for general GitHub REST API failures."""
    pass

class GitHubService:
    """Service to handle communication with the GitHub REST API."""

    def __init__(self, token: Optional[str] = None):
        raw_token = token if token is not None else settings.GITHUB_TOKEN
        self.is_configured = bool(raw_token and raw_token.strip())
        self.is_placeholder = is_placeholder_token(raw_token)

        self.headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "DevLens-App"
        }

        if self.is_configured and not self.is_placeholder:
            self.token = raw_token.strip()
            self.headers["Authorization"] = f"Bearer {self.token}"
            logger.info("GitHubService initialized with configured authorization token.")
        else:
            self.token = None
            if self.is_configured and self.is_placeholder:
                logger.warning(
                    "Configured GITHUB_TOKEN was detected as a placeholder value. "
                    "Proceeding with unauthenticated GitHub API requests."
                )
            else:
                logger.info(
                    "GitHubService initialized without token. "
                    "Proceeding with unauthenticated GitHub API requests."
                )

        # Resilient timeout and retries for REST communication
        self.timeout = httpx.Timeout(connect=15.0, read=20.0, write=10.0, pool=10.0)
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """Returns or lazily creates a reusable httpx.AsyncClient with transport retries."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                transport=httpx.AsyncHTTPTransport(retries=2),
                timeout=self.timeout
            )
        return self._client

    async def aclose(self):
        """Closes underlying client if open."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_repo_metadata(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Retrieves repository metadata from GitHub.

        Args:
            owner: The repository owner's username or organization.
            repo: The repository name.

        Returns:
            Dict containing selected repository metadata fields.

        Raises:
            GitHubNotFoundError: If repository is 404.
            GitHubRateLimitError: If rate limit exceeded.
            GitHubAPIError: For other network or API errors.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}"
        client = self._get_client()

        try:
            response = await client.get(url, headers=self.headers)

            if response.status_code == 200:
                data = response.json()
                return {
                    "owner": data.get("owner", {}).get("login"),
                    "name": data.get("name"),
                    "full_name": data.get("full_name"),
                    "description": data.get("description"),
                    "default_branch": data.get("default_branch", "main"),
                    "visibility": data.get("visibility"),
                    "language": data.get("language"),
                    "stars": data.get("stargazers_count", 0),
                    "forks": data.get("forks_count", 0),
                    "open_issues": data.get("open_issues_count", 0),
                    "url": data.get("html_url"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at")
                }
            elif response.status_code == 401:
                error_msg = _extract_github_error_message(response)
                logger.warning(
                    f"GitHub API authentication failed (401 Unauthorized) for {url}: {error_msg} "
                    f"[token_configured={self.is_configured}, is_placeholder={self.is_placeholder}]"
                )
                raise GitHubAPIError(f"GitHub API authentication failed (401 Unauthorized): {error_msg}")
            elif response.status_code == 404:
                raise GitHubNotFoundError(f"Repository '{owner}/{repo}' not found or is private.")
            elif response.status_code == 403:
                rate_limit_remaining = response.headers.get("x-ratelimit-remaining")
                if rate_limit_remaining == "0":
                    logger.warning(f"GitHub API rate limit exceeded (403) for {url}")
                    raise GitHubRateLimitError("GitHub API rate limit exceeded.")
                error_msg = _extract_github_error_message(response)
                logger.warning(f"GitHub API access forbidden (403) for {url}: {error_msg}")
                raise GitHubAPIError(f"Access forbidden to the requested repository: {error_msg}")
            else:
                error_msg = _extract_github_error_message(response)
                logger.error(f"GitHub API returned unexpected status {response.status_code} for {url}: {error_msg}")
                raise GitHubAPIError(f"GitHub API returned unexpected status {response.status_code}: {error_msg}")

        except httpx.RequestError as e:
            err_detail = str(e) or type(e).__name__
            logger.error(f"Failed to communicate with GitHub API for {url}: {err_detail}")
            raise GitHubAPIError(f"Failed to communicate with GitHub API: {err_detail}")

    async def get_repo_tree(self, owner: str, repo: str, branch: str) -> List[Dict[str, Any]]:
        """
        Retrieves the repository git file tree.

        Args:
            owner: The repository owner.
            repo: The repository name.
            branch: The branch to extract the tree from.

        Returns:
            A list of dictionary files/folders representing the file tree structure.

        Raises:
            GitHubNotFoundError: If repository tree/branch is 404.
            GitHubRateLimitError: If rate limit exceeded.
            GitHubAPIError: For other API issues.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        client = self._get_client()

        try:
            response = await client.get(url, headers=self.headers)

            if response.status_code == 200:
                data = response.json()
                raw_tree = data.get("tree", [])

                formatted_tree = []
                # Limit to 1000 items returned for security, sizing, and performance
                for item in raw_tree[:1000]:
                    path = item.get("path")
                    item_type = item.get("type")

                    if item_type == "tree":
                        mapped_type = "directory"
                    elif item_type == "blob":
                        mapped_type = "file"
                    else:
                        continue # Skip submodules / other types

                    formatted_tree.append({
                        "path": path,
                        "type": mapped_type
                    })
                return formatted_tree

            elif response.status_code == 401:
                error_msg = _extract_github_error_message(response)
                logger.warning(
                    f"GitHub API authentication failed (401 Unauthorized) for {url}: {error_msg} "
                    f"[token_configured={self.is_configured}, is_placeholder={self.is_placeholder}]"
                )
                raise GitHubAPIError(f"GitHub API authentication failed (401 Unauthorized): {error_msg}")
            elif response.status_code == 404:
                raise GitHubNotFoundError(f"Branch/Tree '{branch}' not found for repository.")
            elif response.status_code == 403:
                rate_limit_remaining = response.headers.get("x-ratelimit-remaining")
                if rate_limit_remaining == "0":
                    logger.warning(f"GitHub API rate limit exceeded (403) for {url}")
                    raise GitHubRateLimitError("GitHub API rate limit exceeded.")
                error_msg = _extract_github_error_message(response)
                logger.warning(f"GitHub API access forbidden (403) for {url}: {error_msg}")
                raise GitHubAPIError(f"Access forbidden to the requested branch/tree: {error_msg}")
            else:
                error_msg = _extract_github_error_message(response)
                logger.error(f"GitHub API returned unexpected status {response.status_code} for {url}: {error_msg}")
                raise GitHubAPIError(f"GitHub API returned unexpected status {response.status_code}: {error_msg}")

        except httpx.RequestError as e:
            err_detail = str(e) or type(e).__name__
            logger.error(f"Failed to retrieve tree structure for {url}: {err_detail}")
            raise GitHubAPIError(f"Failed to retrieve tree structure: {err_detail}")

    async def get_file_content(self, owner: str, repo: str, path: str, ref: str) -> str:
        """
        Retrieves the raw text content of a source file using GitHub Contents API.

        Args:
            owner: The repository owner.
            repo: The repository name.
            path: The file path in the repository.
            ref: The commit SHA/branch to retrieve from.

        Returns:
            The raw text content of the file.

        Raises:
            GitHubNotFoundError: If the file is 404.
            GitHubRateLimitError: If rate limit exceeded.
            GitHubAPIError: For other network/API issues.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}"
        headers = {**self.headers, "Accept": "application/vnd.github.raw"}
        client = self._get_client()

        try:
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                return response.text
            elif response.status_code == 401:
                error_msg = _extract_github_error_message(response)
                logger.warning(
                    f"GitHub API authentication failed (401 Unauthorized) for {url}: {error_msg} "
                    f"[token_configured={self.is_configured}, is_placeholder={self.is_placeholder}]"
                )
                raise GitHubAPIError(f"GitHub API authentication failed (401 Unauthorized): {error_msg}")
            elif response.status_code == 404:
                raise GitHubNotFoundError(f"File '{path}' not found in repository.")
            elif response.status_code == 403:
                rate_limit_remaining = response.headers.get("x-ratelimit-remaining")
                if rate_limit_remaining == "0":
                    logger.warning(f"GitHub API rate limit exceeded (403) for {url}")
                    raise GitHubRateLimitError("GitHub API rate limit exceeded.")
                error_msg = _extract_github_error_message(response)
                logger.warning(f"GitHub API access forbidden (403) for {url}: {error_msg}")
                raise GitHubAPIError(f"Access forbidden to the requested file: {error_msg}")
            else:
                error_msg = _extract_github_error_message(response)
                logger.error(f"GitHub API returned unexpected status {response.status_code} for {url}: {error_msg}")
                raise GitHubAPIError(f"GitHub API returned unexpected status {response.status_code}: {error_msg}")

        except httpx.RequestError as e:
            err_detail = str(e) or type(e).__name__
            logger.error(f"Failed to retrieve file content for {url}: {err_detail}")
            raise GitHubAPIError(f"Failed to retrieve file content: {err_detail}")
