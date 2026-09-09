import uuid
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.analysis import AnalysisStatus, AnalysisType
from app.models.ai_models import AIAnalysisReport
from app.services.ai_service import AIRateLimitError
from app.services.repository_persistence import create_or_update_repository
from app.services.analysis_persistence import (
    create_analysis_run,
    save_deterministic_results,
    mark_analysis_completed,
    get_analyses_by_repository,
)

client = TestClient(app)


from app.models.user import User


def test_get_repository_by_id_endpoint(db_session: Session, override_current_user: User):
    """Test GET /api/repositories/{repository_id} endpoint."""
    metadata = {
        "owner": "testorg",
        "name": "project-x",
        "stars": 42,
        "language": "TypeScript",
        "description": "Awesome project"
    }
    repo = create_or_update_repository(
        db_session, metadata, "https://github.com/testorg/project-x", user_id=override_current_user.id
    )

    response = client.get(f"/api/repositories/{repo.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(repo.id)
    assert data["owner"] == "testorg"
    assert data["name"] == "project-x"
    assert data["stars"] == 42


def test_get_repository_by_id_not_found():
    """Test GET /api/repositories/{repository_id} returns 404 for missing repo."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/repositories/{random_id}")
    assert response.status_code == 404
    assert f"Repository '{random_id}' not found" in response.json()["detail"]


def test_get_repository_analyses_endpoint(db_session: Session, override_current_user: User):
    """Test GET /api/repositories/{repository_id}/analyses endpoint."""
    metadata = {"owner": "testorg", "name": "project-y", "stars": 10}
    repo = create_or_update_repository(
        db_session, metadata, "https://github.com/testorg/project-y", user_id=override_current_user.id
    )

    run1 = create_analysis_run(db_session, repo.id, AnalysisType.DETERMINISTIC.value)
    run2 = create_analysis_run(db_session, repo.id, AnalysisType.AI.value)

    response = client.get(f"/api/repositories/{repo.id}/analyses")
    assert response.status_code == 200
    runs = response.json()
    assert len(runs) == 2
    assert runs[0]["id"] == str(run2.id)
    assert runs[1]["id"] == str(run1.id)


def test_get_repository_analyses_not_found():
    """Test GET /api/repositories/{repository_id}/analyses returns 404 for missing repo."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/repositories/{random_id}/analyses")
    assert response.status_code == 404


def test_get_analysis_by_id_endpoint(db_session: Session, override_current_user: User):
    """Test GET /api/analyses/{analysis_id} endpoint."""
    metadata = {"owner": "testorg", "name": "project-z"}
    repo = create_or_update_repository(
        db_session, metadata, "https://github.com/testorg/project-z", user_id=override_current_user.id
    )

    run = create_analysis_run(db_session, repo.id, AnalysisType.DETERMINISTIC.value)
    save_deterministic_results(db_session, run.id, {
        "metrics": {"total_lines": 120},
        "findings": [{"id": "SEC01"}],
    })
    mark_analysis_completed(db_session, run.id)

    response = client.get(f"/api/analyses/{run.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(run.id)
    assert data["repository_id"] == str(repo.id)
    assert data["status"] == "completed"
    assert data["metrics"] == {"total_lines": 120}


def test_get_analysis_by_id_not_found():
    """Test GET /api/analyses/{analysis_id} returns 404 for non-existent run."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/analyses/{random_id}")
    assert response.status_code == 404
    assert f"Analysis run '{random_id}' not found" in response.json()["detail"]


def test_analyze_report_creates_persistence_records(db_session: Session):
    """Test that POST /api/repositories/analyze/report persists repo and completed analysis run."""
    mock_meta = {
        "owner": "persist-owner",
        "name": "persist-repo",
        "full_name": "persist-owner/persist-repo",
        "description": "Persistence test",
        "default_branch": "main",
        "language": "Python",
        "stars": 15,
        "forks": 2,
        "open_issues": 0,
        "url": "https://github.com/persist-owner/persist-repo",
    }
    mock_tree = [{"path": "main.py", "type": "file"}]
    mock_report = {
        "repository": mock_meta,
        "summary": {
            "total_files": 1, "analyzed_files": 1, "skipped_files": 0,
            "source_files": 1, "test_files": 0, "documentation_files": 0,
            "configuration_files": 0, "asset_files": 0, "unknown_files": 0
        },
        "languages": [{"language": "Python", "file_count": 1, "percentage": 100.0}],
        "files": [],
        "metrics": {
            "total_lines": 10, "code_lines": 8, "comment_lines": 1, "blank_lines": 1,
            "largest_files_by_size": [], "largest_files_by_lines": []
        },
        "findings": [],
        "analysis_metadata": {"files_analyzed": 1, "files_skipped": 0, "skip_reasons": {}},
        "tree": [{"path": "main.py", "type": "file"}]
    }

    with patch("app.api.repositories.GitHubService.get_repo_metadata", new_callable=AsyncMock) as mock_get_meta, \
         patch("app.api.repositories.GitHubService.get_repo_tree", new_callable=AsyncMock) as mock_get_tree, \
         patch("app.api.repositories.run_repo_analysis", new_callable=AsyncMock) as mock_run_analysis:

        mock_get_meta.return_value = mock_meta
        mock_get_tree.return_value = mock_tree
        mock_run_analysis.return_value = mock_report

        resp = client.post(
            "/api/repositories/analyze/report",
            json={"url": "https://github.com/persist-owner/persist-repo"}
        )
        assert resp.status_code == 200

        # Verify repo was persisted in DB
        repo_resp = client.get("/api/repositories/analyze/report")  # verify through history
        runs = get_analyses_by_repository(db_session, runs_limit:=10)
        # Check via get_analyses_by_repository
        repo_in_db = create_or_update_repository(db_session, mock_meta, "https://github.com/persist-owner/persist-repo")
        persisted_runs = get_analyses_by_repository(db_session, repo_in_db.id)
        assert len(persisted_runs) == 1
        assert persisted_runs[0].status == AnalysisStatus.COMPLETED.value
        assert persisted_runs[0].analysis_type == AnalysisType.DETERMINISTIC.value
        assert persisted_runs[0].metrics["total_lines"] == 10
        assert repo_in_db.last_analyzed_at is not None


def test_analyze_ai_failure_marks_run_failed(db_session: Session):
    """Test that if AI service fails, the analysis run is saved as FAILED in DB."""
    mock_meta = {
        "owner": "fail-owner",
        "name": "fail-repo",
        "default_branch": "main",
        "language": "Python",
        "stars": 5,
        "forks": 0,
        "open_issues": 0,
        "url": "https://github.com/fail-owner/fail-repo",
    }
    mock_tree = [{"path": "app.py", "type": "file"}]
    mock_report = {
        "repository": mock_meta,
        "summary": {
            "total_files": 1, "analyzed_files": 1, "skipped_files": 0,
            "source_files": 1, "test_files": 0, "documentation_files": 0,
            "configuration_files": 0, "asset_files": 0, "unknown_files": 0
        },
        "languages": [{"language": "Python", "file_count": 1, "percentage": 100.0}],
        "files": [],
        "metrics": {"total_lines": 5, "code_lines": 4, "comment_lines": 0, "blank_lines": 1,
                    "largest_files_by_size": [], "largest_files_by_lines": []},
        "findings": [],
        "analysis_metadata": {"files_analyzed": 1, "files_skipped": 0, "skip_reasons": {}},
        "tree": mock_tree,
        "file_contents": {}
    }

    with patch("app.api.repositories.GitHubService.get_repo_metadata", new_callable=AsyncMock) as mock_get_meta, \
         patch("app.api.repositories.GitHubService.get_repo_tree", new_callable=AsyncMock) as mock_get_tree, \
         patch("app.api.repositories.run_repo_analysis", new_callable=AsyncMock) as mock_run_analysis, \
         patch("app.api.repositories.AIService.analyze_repository", new_callable=AsyncMock) as mock_ai:

        mock_get_meta.return_value = mock_meta
        mock_get_tree.return_value = mock_tree
        mock_run_analysis.return_value = mock_report
        mock_ai.side_effect = AIRateLimitError("Gemini quota exhausted")

        resp = client.post(
            "/api/repositories/analyze/ai",
            json={"url": "https://github.com/fail-owner/fail-repo"}
        )
        assert resp.status_code == 429

        # Verify DB recorded the run as FAILED
        repo = create_or_update_repository(db_session, mock_meta, "https://github.com/fail-owner/fail-repo")
        runs = get_analyses_by_repository(db_session, repo.id)
        assert len(runs) == 1
        assert runs[0].status == AnalysisStatus.FAILED.value
        assert "Gemini quota exhausted" in runs[0].error_message
