import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisStatus, AnalysisType
from app.services.repository_persistence import create_or_update_repository
from app.services.analysis_persistence import (
    create_analysis_run,
    mark_analysis_running,
    save_deterministic_results,
    save_ai_results,
    mark_analysis_completed,
    mark_analysis_failed,
    get_analysis_by_id,
    get_analyses_by_repository,
)


@pytest.fixture
def sample_repo(db_session: Session):
    metadata = {
        "owner": "test-owner",
        "name": "test-repo",
        "stars": 10,
        "language": "Python",
    }
    return create_or_update_repository(db_session, metadata, "https://github.com/test-owner/test-repo")


def test_analysis_run_lifecycle_success(db_session: Session, sample_repo):
    """Test full happy path lifecycle of an analysis run."""
    # 1. Create run
    run = create_analysis_run(db_session, sample_repo.id, AnalysisType.DETERMINISTIC.value)
    assert run.id is not None
    assert run.status == AnalysisStatus.PENDING.value
    assert run.started_at is None
    assert run.completed_at is None

    # 2. Mark running
    running = mark_analysis_running(db_session, run.id)
    assert running.status == AnalysisStatus.RUNNING.value
    assert running.started_at is not None

    # 3. Save deterministic results
    report_data = {
        "summary": {"total_files": 10},
        "metrics": {"total_lines": 500, "code_lines": 400},
        "findings": [{"id": "SEC01", "severity": "medium", "title": "Test Finding"}],
        "languages": [{"language": "Python", "file_count": 8, "percentage": 80.0}],
        "analysis_metadata": {"files_analyzed": 8, "files_skipped": 2},
    }
    saved = save_deterministic_results(db_session, run.id, report_data)
    assert saved.deterministic_result == report_data
    assert saved.metrics == report_data["metrics"]
    assert len(saved.findings) == 1
    assert saved.languages == report_data["languages"]
    assert saved.metadata_json == report_data["analysis_metadata"]

    # 4. Save AI results
    ai_data = {
        "executive_summary": "Solid repository architecture.",
        "strengths": ["Clean separation"],
        "critical_issues": [],
        "architecture_review": {"overview": "Modular"},
        "actionable_recommendations": []
    }
    saved_ai = save_ai_results(db_session, run.id, ai_data)
    assert saved_ai.ai_result == ai_data

    # 5. Mark completed
    completed = mark_analysis_completed(db_session, run.id)
    assert completed.status == AnalysisStatus.COMPLETED.value
    assert completed.completed_at is not None
    assert completed.error_message is None


def test_analysis_run_lifecycle_failure(db_session: Session, sample_repo):
    """Test failure state and error message persistence."""
    run = create_analysis_run(db_session, sample_repo.id, AnalysisType.AI.value)
    mark_analysis_running(db_session, run.id)

    failed = mark_analysis_failed(db_session, run.id, "Rate limit exceeded on Gemini API")
    assert failed.status == AnalysisStatus.FAILED.value
    assert failed.completed_at is not None
    assert failed.error_message == "Rate limit exceeded on Gemini API"


def test_get_analysis_by_id(db_session: Session, sample_repo):
    """Test retrieving analysis run by UUID and string."""
    run = create_analysis_run(db_session, sample_repo.id)

    found_uuid = get_analysis_by_id(db_session, run.id)
    assert found_uuid is not None
    assert found_uuid.id == run.id

    found_str = get_analysis_by_id(db_session, str(run.id))
    assert found_str is not None
    assert found_str.id == run.id

    assert get_analysis_by_id(db_session, "invalid-uuid") is None
    assert get_analysis_by_id(db_session, uuid.uuid4()) is None


def test_get_analyses_by_repository(db_session: Session, sample_repo):
    """Test history querying ordered by created_at desc with pagination limit."""
    run1 = create_analysis_run(db_session, sample_repo.id, AnalysisType.DETERMINISTIC.value)
    run2 = create_analysis_run(db_session, sample_repo.id, AnalysisType.AI.value)
    run3 = create_analysis_run(db_session, sample_repo.id, AnalysisType.FULL.value)

    history = get_analyses_by_repository(db_session, sample_repo.id, limit=2)
    assert len(history) == 2
    # Most recent first
    assert history[0].id == run3.id
    assert history[1].id == run2.id

    all_history = get_analyses_by_repository(db_session, str(sample_repo.id), limit=10)
    assert len(all_history) == 3

    # Non-existent repository
    assert get_analyses_by_repository(db_session, uuid.uuid4()) == []
    assert get_analyses_by_repository(db_session, "not-a-uuid") == []
