import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.repository import Repository
from app.models.analysis import AnalysisRun, AnalysisStatus, AnalysisType


def test_repository_model_creation(db_session: Session):
    """Test creating a Repository instance with defaults and constraints."""
    repo = Repository(
        github_url="https://github.com/octocat/hello-world",
        owner="octocat",
        name="hello-world",
        description="A sample repository",
        stars=100,
        forks=25,
        open_issues=3,
        language="Python",
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)

    assert isinstance(repo.id, uuid.UUID)
    assert repo.github_url == "https://github.com/octocat/hello-world"
    assert repo.owner == "octocat"
    assert repo.name == "hello-world"
    assert repo.default_branch == "main"
    assert repo.stars == 100
    assert repo.forks == 25
    assert not repo.is_private
    assert repo.created_at is not None
    assert repo.updated_at is not None
    assert repo.last_analyzed_at is None
    assert "octocat/hello-world" in repr(repo)


def test_analysis_run_model_creation(db_session: Session):
    """Test creating an AnalysisRun instance with defaults and payloads."""
    repo = Repository(
        github_url="https://github.com/octocat/spoon-knife",
        owner="octocat",
        name="spoon-knife",
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)

    run = AnalysisRun(
        repository_id=repo.id,
        status=AnalysisStatus.PENDING.value,
        analysis_type=AnalysisType.DETERMINISTIC.value,
        metrics={"total_lines": 500, "code_lines": 400},
        findings=[{"id": "SEC001", "severity": "high", "title": "Hardcoded key"}],
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    assert isinstance(run.id, uuid.UUID)
    assert run.repository_id == repo.id
    assert run.status == "pending"
    assert run.analysis_type == "deterministic"
    assert run.metrics == {"total_lines": 500, "code_lines": 400}
    assert len(run.findings) == 1
    assert run.findings[0]["id"] == "SEC001"
    assert run.created_at is not None
    assert "AnalysisRun" in repr(run)


def test_analysis_run_status_validation():
    """Test validator enforces valid AnalysisStatus enum values."""
    with pytest.raises(ValueError, match="Invalid analysis status"):
        AnalysisRun(
            repository_id=uuid.uuid4(),
            status="invalid_status"
        )


def test_analysis_run_type_validation():
    """Test validator enforces valid AnalysisType enum values."""
    with pytest.raises(ValueError, match="Invalid analysis type"):
        AnalysisRun(
            repository_id=uuid.uuid4(),
            analysis_type="invalid_type"
        )


def test_cascade_delete_repository(db_session: Session):
    """Test deleting a Repository cascades and deletes associated AnalysisRuns."""
    repo = Repository(
        github_url="https://github.com/octocat/cascade-test",
        owner="octocat",
        name="cascade-test",
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)

    run1 = AnalysisRun(repository_id=repo.id, status=AnalysisStatus.COMPLETED.value)
    run2 = AnalysisRun(repository_id=repo.id, status=AnalysisStatus.FAILED.value)
    db_session.add_all([run1, run2])
    db_session.commit()

    # Verify runs exist
    runs = db_session.scalars(
        select(AnalysisRun).where(AnalysisRun.repository_id == repo.id)
    ).all()
    assert len(runs) == 2

    # Delete repository
    db_session.delete(repo)
    db_session.commit()

    # Verify runs were cascade-deleted
    remaining_runs = db_session.scalars(
        select(AnalysisRun).where(AnalysisRun.repository_id == repo.id)
    ).all()
    assert len(remaining_runs) == 0
