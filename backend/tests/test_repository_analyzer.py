from unittest.mock import AsyncMock, patch
import pytest
from app.analyzers.repository_analyzer import analyze_repository

# Enable asyncio in pytest (anyio is default installed)
pytestmark = pytest.mark.anyio

async def test_analyze_repository_pipeline():
    mock_metadata = {
        "owner": "owner",
        "name": "devlens",
        "full_name": "owner/devlens",
        "description": "Scaffolding repo description",
        "default_branch": "main",
        "stars": 10,
        "forks": 2,
        "open_issues": 1,
        "url": "https://github.com/owner/devlens"
    }

    mock_tree = [
        {"path": "README.md", "type": "file"},
        {"path": "src/main.py", "type": "file"},
        {"path": "tests/test_main.py", "type": "file"},
        {"path": "package.json", "type": "file"},
        {"path": "logo.png", "type": "file"}
    ]

    # Contents of files to return when fetched
    files_contents = {
        "README.md": "# DevLens Scaffolding",
        "src/main.py": """# Main entrypoint
def run():
    API_KEY = "sk-proj-abc123xyz" # Potential secret
    print("Running...") # Debug statement
""",
        "tests/test_main.py": """# Test main
def test_run():
    assert True
""",
        "package.json": '{"name": "frontend"}'
    }

    async def mock_get_content(owner, repo, path, ref):
        if path in files_contents:
            return files_contents[path]
        raise Exception("File not found in mock config")

    # Patch GitHubService.get_file_content
    with patch("app.analyzers.repository_analyzer.GitHubService.get_file_content", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = mock_get_content
        
        report = await analyze_repository("owner", "devlens", mock_metadata, mock_tree)
        
        # Verify structure
        assert report["repository"]["name"] == "devlens"
        
        # Summary checks
        summary = report["summary"]
        assert summary["total_files"] == 5
        # We only analyze "source" and "test" files (src/main.py and tests/test_main.py)
        assert summary["analyzed_files"] == 2
        assert summary["source_files"] == 1
        assert summary["test_files"] == 1
        assert summary["documentation_files"] == 1
        assert summary["configuration_files"] == 1
        assert summary["asset_files"] == 1  # logo.png matches asset ext (.png)
        
        # Metrics checks
        metrics = report["metrics"]
        assert metrics["total_lines"] > 0
        assert len(metrics["largest_files_by_size"]) == 2
        assert len(metrics["largest_files_by_lines"]) == 2
        
        # Language distribution checks
        languages = report["languages"]
        assert len(languages) == 1
        assert languages[0]["language"] == "Python"
        assert languages[0]["percentage"] == 100.0
        
        # Findings checks
        findings = report["findings"]
        # src/main.py has: TODO/secrets/broadexcept/print checks
        # Matches: API_KEY secret assignment, print statement. No broad except or TODO.
        assert len(findings) == 2
        assert any(f["title"] == "Potential Hardcoded Credential" for f in findings)
        assert any(f["title"] == "Debug Print Statement" for f in findings)
