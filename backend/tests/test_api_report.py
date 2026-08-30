from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.github_service import GitHubNotFoundError, GitHubRateLimitError, GitHubAPIError

client = TestClient(app)

def test_analyze_repository_report_success():
    """
    Test successful generation and return of a full AnalysisReport.
    """
    mock_metadata = {
        "owner": "owner-name",
        "name": "devlens",
        "full_name": "owner-name/devlens",
        "description": "Repo description",
        "default_branch": "main",
        "visibility": "public",
        "language": "Python",
        "stars": 100,
        "forks": 10,
        "open_issues": 5,
        "url": "https://github.com/owner-name/devlens"
    }

    mock_tree = [
        {"path": "src/main.py", "type": "file"},
        {"path": "README.md", "type": "file"}
    ]

    mock_report = {
        "repository": {
            "owner": "owner-name",
            "name": "devlens",
            "full_name": "owner-name/devlens",
            "description": "Repo description",
            "default_branch": "main",
            "language": "Python",
            "stars": 100,
            "forks": 10,
            "open_issues": 5,
            "url": "https://github.com/owner-name/devlens"
        },
        "summary": {
            "total_files": 2,
            "analyzed_files": 1,
            "skipped_files": 0,
            "source_files": 1,
            "test_files": 0,
            "documentation_files": 1,
            "configuration_files": 0,
            "asset_files": 0,
            "unknown_files": 0
        },
        "languages": [
            {"language": "Python", "file_count": 1, "percentage": 100.0}
        ],
        "files": [
            {
                "path": "src/main.py",
                "language": "Python",
                "category": "source",
                "size_bytes": 128,
                "line_count": 10,
                "code_lines": 8,
                "comment_lines": 1,
                "blank_lines": 1
            }
        ],
        "metrics": {
            "total_lines": 10,
            "code_lines": 8,
            "comment_lines": 1,
            "blank_lines": 1,
            "largest_files_by_size": [{"path": "src/main.py", "size_bytes": 128}],
            "largest_files_by_lines": [{"path": "src/main.py", "line_count": 10}]
        },
        "findings": [
            {
                "id": "QLT-002-src-main.py-5",
                "severity": "info",
                "category": "quality",
                "title": "Unresolved TODO Comment",
                "description": "Found TODO comments: '# TODO: check this'",
                "file": "src/main.py",
                "line": 5,
                "recommendation": "Review TODO."
            }
        ],
        "analysis_metadata": {
            "files_analyzed": 1,
            "files_skipped": 0,
            "skip_reasons": {"too_large": 0, "unsupported": 0, "limit_exceeded": 0}
        },
        "tree": [
            {"path": "src/main.py", "type": "file"},
            {"path": "README.md", "type": "file"}
        ]
    }

    with patch("app.api.repositories.GitHubService.get_repo_metadata", new_callable=AsyncMock) as mock_meta, \
         patch("app.api.repositories.GitHubService.get_repo_tree", new_callable=AsyncMock) as mock_tree_svc, \
         patch("app.api.repositories.run_repo_analysis", new_callable=AsyncMock) as mock_run_analysis:
         
        mock_meta.return_value = mock_metadata
        mock_tree_svc.return_value = mock_tree
        mock_run_analysis.return_value = mock_report
        
        response = client.post(
            "/api/repositories/analyze/report",
            json={"url": "https://github.com/owner-name/devlens"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["repository"]["name"] == "devlens"
        assert data["summary"]["total_files"] == 2
        assert len(data["findings"]) == 1
        assert data["findings"][0]["title"] == "Unresolved TODO Comment"

def test_analyze_repository_report_invalid_url():
    """
    Test that invalid URL format returns 400.
    """
    response = client.post(
        "/api/repositories/analyze/report",
        json={"url": "https://github.com/owner/repo/pull/15/report"}
    )
    assert response.status_code == 400
    assert "Invalid GitHub" in response.json()["detail"]
