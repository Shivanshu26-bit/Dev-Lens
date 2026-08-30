import pytest
from app.services.github_url import parse_github_url

def test_parse_valid_urls():
    """
    Test standard valid GitHub URL formats.
    """
    assert parse_github_url("https://github.com/user/repo") == ("user", "repo")
    assert parse_github_url("https://github.com/user/repo/") == ("user", "repo")
    assert parse_github_url("http://github.com/user/repo") == ("user", "repo")
    assert parse_github_url("https://www.github.com/user/repo") == ("user", "repo")
    assert parse_github_url("https://github.com/user/repo.git") == ("user", "repo")
    assert parse_github_url("  https://github.com/user-name/repo-name  ") == ("user-name", "repo-name")

def test_parse_invalid_urls():
    """
    Test invalid GitHub URL structures which should raise ValueError.
    """
    invalid_urls = [
        "https://github.com/user",              # Missing repository name
        "https://github.com/user/repo/issues",   # Subpath issues
        "https://github.com/user/repo/pull/12",  # Subpath pull request
        "https://github.com/user/repo/settings",  # Subpath settings
        "https://google.com/user/repo",         # Invalid domain
        "github.com/user/repo",                 # Missing protocol
        "",                                     # Empty string
        "   ",                                  # Whitespace
        "https://github.com/./repo",            # Invalid dot characters
        "https://github.com/user/."
    ]
    
    for url in invalid_urls:
        with pytest.raises(ValueError) as exc_info:
            parse_github_url(url)
        assert "Invalid GitHub" in str(exc_info.value) or "Invalid owner" in str(exc_info.value)
