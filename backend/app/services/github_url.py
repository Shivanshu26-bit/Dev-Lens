import re
from typing import Tuple

# Match exactly https://github.com/owner/repo or https://github.com/owner/repo/
# Group 1: owner, Group 2: repository
GITHUB_URL_PATTERN = re.compile(
    r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/?$"
)

def parse_github_url(url: str) -> Tuple[str, str]:
    """
    Parses a GitHub repository URL to extract the owner and repository name.
    
    Args:
        url: The full GitHub repository URL.
        
    Returns:
        A tuple of (owner, repository_name).
        
    Raises:
        ValueError: If the URL is not a valid GitHub repository URL.
    """
    clean_url = url.strip()
    match = GITHUB_URL_PATTERN.match(clean_url)
    
    if not match:
        raise ValueError(
            "Invalid GitHub repository URL. Must be formatted like: "
            "https://github.com/owner/repo"
        )
        
    owner, repo = match.groups()
    
    # Strip any trailing slashes
    repo = repo.rstrip('/')
    
    # Strip optional .git suffix if present
    if repo.lower().endswith(".git"):
        repo = repo[:-4]
        
    # Additional basic sanity checks
    if not owner or not repo or owner in (".", "..") or repo in (".", ".."):
        raise ValueError("Invalid owner or repository name extracted from URL")
        
    # Ensure there are no subpaths (like /issues or /settings)
    if "/" in owner or "/" in repo:
        raise ValueError("Invalid GitHub URL: nested subpaths are not supported")
        
    return owner, repo
