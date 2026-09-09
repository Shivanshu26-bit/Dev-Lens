from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.github_service import GitHubNotFoundError
from app.services.ai_service import (
    AIConfigError,
    AIRateLimitError,
    AITimeoutError,
    AIServiceError,
)
from app.models.ai_models import AIAnalysisReport

client = TestClient(app)


def get_mock_ai_report():
    return AIAnalysisReport.model_validate({
        "executive_summary": "Solid application structure.",
        "architecture": {
            "rating": "good",
            "assessment": "Modular design.",
            "strengths": ["Clear boundaries"],
            "weaknesses": []
        },
        "security": {
            "rating": "good",
            "assessment": "Secure defaults.",
            "strengths": [],
            "weaknesses": [],
            "important_issues": [],
            "recommendations": []
        },
        "performance": {
            "rating": "good",
            "assessment": "Efficient execution.",
            "recommendations": []
        },
        "maintainability": {
            "rating": "excellent",
            "assessment": "Well documented.",
            "recommendations": []
        },
        "documentation": {
            "rating": "good",
            "assessment": "Clear README.",
            "recommendations": []
        },
        "strengths": ["Clean structure"],
        "priorities": [
            {
                "priority": "low",
                "category": "Documentation",
                "title": "Add API examples",
                "explanation": "Makes onboarding faster.",
                "recommendation": "Add curl examples.",
                "evidence": "README.md"
            }
        ],
        "confidence": "high",
        "confidence_reason": None
    })


def get_mock_deterministic_report():
    return {
        "repository": {
            "owner": "test-owner",
            "name": "devlens",
            "full_name": "test-owner/devlens",
            "description": "Test repo",
            "default_branch": "main",
            "language": "Python",
            "stars": 42,
            "forks": 5,
            "open_issues": 1,
            "url": "https://github.com/test-owner/devlens"
        },
        "summary": {
            "total_files": 1,
            "analyzed_files": 1,
            "skipped_files": 0,
            "source_files": 1,
            "test_files": 0,
            "documentation_files": 0,
            "configuration_files": 0,
            "asset_files": 0,
            "unknown_files": 0
        },
        "languages": [
            {"language": "Python", "file_count": 1, "percentage": 100.0}
        ],
        "files": [
            {
                "path": "main.py",
                "language": "Python",
                "category": "source",
                "size_bytes": 100,
                "line_count": 5,
                "code_lines": 5,
                "comment_lines": 0,
                "blank_lines": 0
            }
        ],
        "metrics": {
            "total_lines": 5,
            "code_lines": 5,
            "comment_lines": 0,
            "blank_lines": 0,
            "largest_files_by_size": [{"path": "main.py", "size_bytes": 100}],
            "largest_files_by_lines": [{"path": "main.py", "line_count": 5}]
        },
        "findings": [],
        "analysis_metadata": {
            "files_analyzed": 1,
            "files_skipped": 0,
            "skip_reasons": {"too_large": 0, "unsupported": 0, "limit_exceeded": 0}
        },
        "tree": [
            {"path": "main.py", "type": "file"}
        ],
        "file_contents": {
            "main.py": "print('hello world')"
        }
    }


def test_analyze_repository_ai_success():
    mock_metadata = {
        "owner": "test-owner",
        "name": "devlens",
        "full_name": "test-owner/devlens",
        "default_branch": "main",
        "stars": 42,
        "forks": 5,
        "open_issues": 1,
        "url": "https://github.com/test-owner/devlens"
    }

    mock_tree = [{"path": "main.py", "type": "file"}]
    mock_det = get_mock_deterministic_report()
    mock_ai = get_mock_ai_report()

    with patch("app.api.repositories.GitHubService.get_repo_metadata", new_callable=AsyncMock) as mock_meta, \
         patch("app.api.repositories.GitHubService.get_repo_tree", new_callable=AsyncMock) as mock_tree_svc, \
         patch("app.api.repositories.run_repo_analysis", new_callable=AsyncMock) as mock_det_svc, \
         patch("app.api.repositories.AIService.analyze_repository", new_callable=AsyncMock) as mock_ai_svc:

        mock_meta.return_value = mock_metadata
        mock_tree_svc.return_value = mock_tree
        mock_det_svc.return_value = mock_det
        mock_ai_svc.return_value = mock_ai

        response = client.post(
            "/api/repositories/analyze/ai",
            json={"url": "https://github.com/test-owner/devlens"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "repository" in data
        assert "deterministic_analysis" in data
        assert "ai_analysis" in data
        assert data["ai_analysis"]["architecture"]["rating"] == "good"
        assert data["ai_analysis"]["executive_summary"] == "Solid application structure."
        assert len(data["ai_analysis"]["priorities"]) == 1


def test_analyze_repository_ai_invalid_url():
    response = client.post(
        "/api/repositories/analyze/ai",
        json={"url": "https://not-github.com/owner/repo"}
    )
    assert response.status_code == 400


def test_analyze_repository_ai_repo_not_found():
    with patch("app.api.repositories.GitHubService.get_repo_metadata", new_callable=AsyncMock) as mock_meta:
        mock_meta.side_effect = GitHubNotFoundError("Repo not found")
        response = client.post(
            "/api/repositories/analyze/ai",
            json={"url": "https://github.com/test-owner/nonexistent"}
        )
        assert response.status_code == 404


def test_analyze_repository_ai_missing_key_failure():
    mock_metadata = {"owner": "test-owner", "name": "devlens", "default_branch": "main"}
    mock_tree = [{"path": "main.py", "type": "file"}]
    mock_det = get_mock_deterministic_report()

    with patch("app.api.repositories.GitHubService.get_repo_metadata", new_callable=AsyncMock) as mock_meta, \
         patch("app.api.repositories.GitHubService.get_repo_tree", new_callable=AsyncMock) as mock_tree_svc, \
         patch("app.api.repositories.run_repo_analysis", new_callable=AsyncMock) as mock_det_svc, \
         patch("app.api.repositories.AIService.analyze_repository", new_callable=AsyncMock) as mock_ai_svc:

        mock_meta.return_value = mock_metadata
        mock_tree_svc.return_value = mock_tree
        mock_det_svc.return_value = mock_det
        mock_ai_svc.side_effect = AIConfigError("Gemini API key is not configured.")

        response = client.post(
            "/api/repositories/analyze/ai",
            json={"url": "https://github.com/test-owner/devlens"}
        )
        assert response.status_code == 503
        assert "Gemini API key is not configured" in response.json()["detail"]


def test_analyze_repository_ai_rate_limit_failure():
    mock_metadata = {"owner": "test-owner", "name": "devlens", "default_branch": "main"}
    mock_tree = [{"path": "main.py", "type": "file"}]
    mock_det = get_mock_deterministic_report()

    with patch("app.api.repositories.GitHubService.get_repo_metadata", new_callable=AsyncMock) as mock_meta, \
         patch("app.api.repositories.GitHubService.get_repo_tree", new_callable=AsyncMock) as mock_tree_svc, \
         patch("app.api.repositories.run_repo_analysis", new_callable=AsyncMock) as mock_det_svc, \
         patch("app.api.repositories.AIService.analyze_repository", new_callable=AsyncMock) as mock_ai_svc:

        mock_meta.return_value = mock_metadata
        mock_tree_svc.return_value = mock_tree
        mock_det_svc.return_value = mock_det
        mock_ai_svc.side_effect = AIRateLimitError("Gemini API rate limit exceeded.")

        response = client.post(
            "/api/repositories/analyze/ai",
            json={"url": "https://github.com/test-owner/devlens"}
        )
        assert response.status_code == 429
