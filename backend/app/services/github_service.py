from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings

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
        # Allow passing token, otherwise fallback to configured settings
        self.token = token or settings.GITHUB_TOKEN
        self.headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "DevLens-App"
        }
        
        # Append authorization token if configured
        if self.token and self.token.strip():
            self.headers["Authorization"] = f"Bearer {self.token.strip()}"
            
        # 10 second timeout for REST communication
        self.timeout = 10.0

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
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
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
                elif response.status_code == 404:
                    raise GitHubNotFoundError(f"Repository '{owner}/{repo}' not found or is private.")
                elif response.status_code == 403:
                    # Check if standard limit headers indicate block
                    rate_limit_remaining = response.headers.get("x-ratelimit-remaining")
                    if rate_limit_remaining == "0":
                        raise GitHubRateLimitError("GitHub API rate limit exceeded.")
                    raise GitHubAPIError("Access forbidden to the requested repository.")
                else:
                    raise GitHubAPIError(f"GitHub API returned unexpected status {response.status_code}")
                    
            except httpx.RequestError as e:
                raise GitHubAPIError(f"Failed to communicate with GitHub API: {str(e)}")

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
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
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
                    
                elif response.status_code == 404:
                    raise GitHubNotFoundError(f"Branch/Tree '{branch}' not found for repository.")
                elif response.status_code == 403:
                    rate_limit_remaining = response.headers.get("x-ratelimit-remaining")
                    if rate_limit_remaining == "0":
                        raise GitHubRateLimitError("GitHub API rate limit exceeded.")
                    raise GitHubAPIError("Access forbidden to the requested branch/tree.")
                else:
                    raise GitHubAPIError(f"GitHub API returned unexpected status {response.status_code}")
                    
            except httpx.RequestError as e:
                raise GitHubAPIError(f"Failed to retrieve tree structure: {str(e)}")

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
        
        # Request raw contents format
        headers = {**self.headers, "Accept": "application/vnd.github.raw"}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 404:
                    raise GitHubNotFoundError(f"File '{path}' not found in repository.")
                elif response.status_code == 403:
                    rate_limit_remaining = response.headers.get("x-ratelimit-remaining")
                    if rate_limit_remaining == "0":
                        raise GitHubRateLimitError("GitHub API rate limit exceeded.")
                    raise GitHubAPIError("Access forbidden to the requested file.")
                else:
                    raise GitHubAPIError(f"GitHub API returned unexpected status {response.status_code} for file retrieval.")
                    
            except httpx.RequestError as e:
                raise GitHubAPIError(f"Failed to retrieve file content: {str(e)}")

