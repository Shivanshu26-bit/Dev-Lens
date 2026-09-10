import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.repository import Repository
from app.models.analysis import AnalysisRun, AnalysisStatus, AnalysisType
from app.services.repository_persistence import (
    create_or_update_repository,
    compute_pct_change,
    get_repository_trends,
)
from app.services.analysis_persistence import (
    create_analysis_run,
    save_deterministic_results,
    save_ai_results,
    mark_analysis_running,
    mark_analysis_completed,
    mark_analysis_failed,
)

client = TestClient(app)


def test_compute_pct_change_unit():
    """Unit tests for compute_pct_change verifying edge cases and division-by-zero safety."""
    assert compute_pct_change(None, None) is None
    assert compute_pct_change(100, None) is None
    assert compute_pct_change(None, 100) is None
    # 0 to 0 is 0.0% change
    assert compute_pct_change(0, 0) == 0.0
    # Division by zero returns None (never NaN or Infinity)
    assert compute_pct_change(100, 0) is None
    assert compute_pct_change(-50, 0) is None
    # Normal calculations
    assert compute_pct_change(150, 100) == 50.0
    assert compute_pct_change(50, 100) == -50.0
    assert compute_pct_change(0, 100) == -100.0
    assert compute_pct_change(4, 3) == 33.33
    assert compute_pct_change(2, 3) == -33.33


def test_get_trends_zero_runs(db_session: Session, override_current_user: User):
    """Test GET /api/repositories/{id}/trends with 0 analysis runs."""
    meta = {"owner": "testorg", "name": "empty-repo"}
    repo = create_or_update_repository(
        db_session, meta, "https://github.com/testorg/empty-repo", user_id=override_current_user.id
    )

    response = client.get(f"/api/repositories/{repo.id}/trends")
    assert response.status_code == 200
    data = response.json()
    assert data["repository_id"] == str(repo.id)
    assert data["owner"] == "testorg"
    assert data["name"] == "empty-repo"
    assert data["github_url"] == "https://github.com/testorg/empty-repo"
    assert data["total_runs_analyzed"] == 0
    assert data["trends"] == []


def test_get_trends_one_run(db_session: Session, override_current_user: User):
    """Test GET /api/repositories/{id}/trends with 1 completed run returns null deltas."""
    meta = {"owner": "testorg", "name": "single-run-repo"}
    repo = create_or_update_repository(
        db_session, meta, "https://github.com/testorg/single-run-repo", user_id=override_current_user.id
    )

    run = create_analysis_run(db_session, repo.id, AnalysisType.DETERMINISTIC.value)
    save_deterministic_results(db_session, run.id, {
        "metrics": {"total_lines": 5000, "code_lines": 4200},
        "summary": {"total_files": 35},
        "findings": [{"id": "F1"}, {"id": "F2"}, {"id": "F3"}]
    })
    mark_analysis_completed(db_session, run.id)

    response = client.get(f"/api/repositories/{repo.id}/trends")
    assert response.status_code == 200
    data = response.json()
    assert data["total_runs_analyzed"] == 1
    assert len(data["trends"]) == 1

    pt = data["trends"][0]
    assert pt["analysis_id"] == str(run.id)
    assert pt["analysis_type"] == "deterministic"
    assert pt["total_lines"] == 5000
    assert pt["code_lines"] == 4200
    assert pt["total_files"] == 35
    assert pt["findings_count"] == 3

    # First point must have null deltas and null percentage changes
    assert pt["delta_total_lines"] is None
    assert pt["delta_code_lines"] is None
    assert pt["delta_total_files"] is None
    assert pt["delta_findings_count"] is None
    assert pt["pct_change_total_lines"] is None
    assert pt["pct_change_code_lines"] is None
    assert pt["pct_change_total_files"] is None
    assert pt["pct_change_findings_count"] is None


def test_get_trends_multiple_runs_chronology(db_session: Session, override_current_user: User):
    """Test GET /api/repositories/{id}/trends returns runs in strict ascending chronological order."""
    now = datetime.now(timezone.utc)
    meta = {"owner": "testorg", "name": "chrono-repo"}
    repo = create_or_update_repository(
        db_session, meta, "https://github.com/testorg/chrono-repo", user_id=override_current_user.id
    )

    # Insert out of order: run2 (middle), run3 (newest), run1 (oldest)
    run2 = create_analysis_run(db_session, repo.id, AnalysisType.DETERMINISTIC.value)
    run2.created_at = now - timedelta(days=2)
    save_deterministic_results(db_session, run2.id, {
        "metrics": {"total_lines": 2000, "code_lines": 1600},
        "summary": {"total_files": 20},
        "findings": [{"id": "F1"}]
    })
    mark_analysis_completed(db_session, run2.id)

    run3 = create_analysis_run(db_session, repo.id, AnalysisType.DETERMINISTIC.value)
    run3.created_at = now - timedelta(days=1)
    save_deterministic_results(db_session, run3.id, {
        "metrics": {"total_lines": 2500, "code_lines": 2000},
        "summary": {"total_files": 25},
        "findings": [{"id": "F1"}, {"id": "F2"}]
    })
    mark_analysis_completed(db_session, run3.id)

    run1 = create_analysis_run(db_session, repo.id, AnalysisType.DETERMINISTIC.value)
    run1.created_at = now - timedelta(days=3)
    save_deterministic_results(db_session, run1.id, {
        "metrics": {"total_lines": 1000, "code_lines": 800},
        "summary": {"total_files": 10},
        "findings": []
    })
    mark_analysis_completed(db_session, run1.id)

    db_session.commit()

    response = client.get(f"/api/repositories/{repo.id}/trends")
    assert response.status_code == 200
    data = response.json()
    assert data["total_runs_analyzed"] == 3

    trends = data["trends"]
    assert trends[0]["analysis_id"] == str(run1.id)
    assert trends[1]["analysis_id"] == str(run2.id)
    assert trends[2]["analysis_id"] == str(run3.id)

    # Verify Run 2 comparisons against Run 1
    assert trends[1]["delta_total_lines"] == 1000
    assert trends[1]["delta_code_lines"] == 800
    assert trends[1]["delta_total_files"] == 10
    assert trends[1]["delta_findings_count"] == 1
    assert trends[1]["pct_change_total_lines"] == 100.0
    assert trends[1]["pct_change_code_lines"] == 100.0
    assert trends[1]["pct_change_total_files"] == 100.0
    assert trends[1]["pct_change_findings_count"] is None  # 0 -> 1 division by zero safe handling

    # Verify Run 3 comparisons against Run 2
    assert trends[2]["delta_total_lines"] == 500
    assert trends[2]["delta_code_lines"] == 400
    assert trends[2]["delta_total_files"] == 5
    assert trends[2]["delta_findings_count"] == 1
    assert trends[2]["pct_change_total_lines"] == 25.0
    assert trends[2]["pct_change_code_lines"] == 25.0
    assert trends[2]["pct_change_total_files"] == 25.0
    assert trends[2]["pct_change_findings_count"] == 100.0


def test_get_trends_positive_and_negative_deltas(db_session: Session, override_current_user: User):
    """Test positive and negative deltas and percentage changes across sequential runs."""
    now = datetime.now(timezone.utc)
    meta = {"owner": "testorg", "name": "delta-repo"}
    repo = create_or_update_repository(
        db_session, meta, "https://github.com/testorg/delta-repo", user_id=override_current_user.id
    )

    # Run 1: baseline
    run1 = create_analysis_run(db_session, repo.id, AnalysisType.DETERMINISTIC.value)
    run1.created_at = now - timedelta(days=2)
    save_deterministic_results(db_session, run1.id, {
        "metrics": {"total_lines": 1000, "code_lines": 800},
        "summary": {"total_files": 10},
        "findings": [{"id": f"F{i}"} for i in range(10)]
    })
    mark_analysis_completed(db_session, run1.id)

    # Run 2: increases in lines and files, decrease in findings
    run2 = create_analysis_run(db_session, repo.id, AnalysisType.DETERMINISTIC.value)
    run2.created_at = now - timedelta(days=1)
    save_deterministic_results(db_session, run2.id, {
        "metrics": {"total_lines": 1500, "code_lines": 1200},
        "summary": {"total_files": 12},
        "findings": [{"id": f"F{i}"} for i in range(5)]
    })
    mark_analysis_completed(db_session, run2.id)

    # Run 3: decreases in lines and files, increase in findings
    run3 = create_analysis_run(db_session, repo.id, AnalysisType.DETERMINISTIC.value)
    run3.created_at = now
    save_deterministic_results(db_session, run3.id, {
        "metrics": {"total_lines": 1200, "code_lines": 900},
        "summary": {"total_files": 8},
        "findings": [{"id": f"F{i}"} for i in range(8)]
    })
    mark_analysis_completed(db_session, run3.id)

    db_session.commit()

    response = client.get(f"/api/repositories/{repo.id}/trends")
    assert response.status_code == 200
    data = response.json()
    trends = data["trends"]

    # Point 1 (Run 2 compared to Run 1)
    pt1 = trends[1]
    assert pt1["delta_total_lines"] == 500
    assert pt1["pct_change_total_lines"] == 50.0
    assert pt1["delta_code_lines"] == 400
    assert pt1["pct_change_code_lines"] == 50.0
    assert pt1["delta_total_files"] == 2
    assert pt1["pct_change_total_files"] == 20.0
    assert pt1["delta_findings_count"] == -5
    assert pt1["pct_change_findings_count"] == -50.0

    # Point 2 (Run 3 compared to Run 2)
    pt2 = trends[2]
    assert pt2["delta_total_lines"] == -300
    assert pt2["pct_change_total_lines"] == -20.0
    assert pt2["delta_code_lines"] == -300
    assert pt2["pct_change_code_lines"] == -25.0
    assert pt2["delta_total_files"] == -4
    assert pt2["pct_change_total_files"] == -33.33
    assert pt2["delta_findings_count"] == 3
    assert pt2["pct_change_findings_count"] == 60.0


def test_get_trends_previous_value_zero(db_session: Session, override_current_user: User):
    """Test safe zero-handling when previous metric value is 0 (no NaN or Infinity)."""
    now = datetime.now(timezone.utc)
    meta = {"owner": "testorg", "name": "zero-repo"}
    repo = create_or_update_repository(
        db_session, meta, "https://github.com/testorg/zero-repo", user_id=override_current_user.id
    )

    # Run 1: 0 findings, 0 lines, 0 code_lines, 0 files
    run1 = create_analysis_run(db_session, repo.id, AnalysisType.DETERMINISTIC.value)
    run1.created_at = now - timedelta(days=1)
    save_deterministic_results(db_session, run1.id, {
        "metrics": {"total_lines": 0, "code_lines": 0},
        "summary": {"total_files": 0},
        "findings": []
    })
    mark_analysis_completed(db_session, run1.id)

    # Run 2: 0 findings, 100 lines, 0 code_lines, 5 files
    run2 = create_analysis_run(db_session, repo.id, AnalysisType.DETERMINISTIC.value)
    run2.created_at = now
    save_deterministic_results(db_session, run2.id, {
        "metrics": {"total_lines": 100, "code_lines": 0},
        "summary": {"total_files": 5},
        "findings": []
    })
    mark_analysis_completed(db_session, run2.id)

    db_session.commit()

    response = client.get(f"/api/repositories/{repo.id}/trends")
    assert response.status_code == 200
    data = response.json()
    pt = data["trends"][1]

    # findings_count: 0 -> 0: delta = 0, pct_change = 0.0
    assert pt["delta_findings_count"] == 0
    assert pt["pct_change_findings_count"] == 0.0

    # code_lines: 0 -> 0: delta = 0, pct_change = 0.0
    assert pt["delta_code_lines"] == 0
    assert pt["pct_change_code_lines"] == 0.0

    # total_lines: 0 -> 100: delta = 100, pct_change = None (division by zero)
    assert pt["delta_total_lines"] == 100
    assert pt["pct_change_total_lines"] is None

    # total_files: 0 -> 5: delta = 5, pct_change = None (division by zero)
    assert pt["delta_total_files"] == 5
    assert pt["pct_change_total_files"] is None


def test_get_trends_deterministic_and_ai_runs(db_session: Session, override_current_user: User):
    """Test trends preserve analysis_type ('deterministic' and 'ai') across sequential runs."""
    now = datetime.now(timezone.utc)
    meta = {"owner": "testorg", "name": "mixed-repo"}
    repo = create_or_update_repository(
        db_session, meta, "https://github.com/testorg/mixed-repo", user_id=override_current_user.id
    )

    # Run 1: deterministic run
    run1 = create_analysis_run(db_session, repo.id, AnalysisType.DETERMINISTIC.value)
    run1.created_at = now - timedelta(hours=2)
    save_deterministic_results(db_session, run1.id, {
        "metrics": {"total_lines": 3000, "code_lines": 2500},
        "summary": {"total_files": 15},
        "findings": [{"id": "F1"}, {"id": "F2"}]
    })
    mark_analysis_completed(db_session, run1.id)

    # Run 2: AI run
    run2 = create_analysis_run(db_session, repo.id, AnalysisType.AI.value)
    run2.created_at = now - timedelta(hours=1)
    save_deterministic_results(db_session, run2.id, {
        "metrics": {"total_lines": 3200, "code_lines": 2700},
        "summary": {"total_files": 16},
        "findings": [{"id": "F1"}]
    })
    save_ai_results(db_session, run2.id, {"executive_summary": "Good project"})
    mark_analysis_completed(db_session, run2.id)

    db_session.commit()

    response = client.get(f"/api/repositories/{repo.id}/trends")
    assert response.status_code == 200
    data = response.json()
    assert data["total_runs_analyzed"] == 2

    pt1, pt2 = data["trends"]
    assert pt1["analysis_type"] == "deterministic"
    assert pt2["analysis_type"] == "ai"
    assert pt2["delta_total_lines"] == 200
    assert pt2["delta_findings_count"] == -1


def test_get_trends_ignores_non_completed_runs(db_session: Session, override_current_user: User):
    """Test pending, running, and failed runs are excluded from trend calculations."""
    now = datetime.now(timezone.utc)
    meta = {"owner": "testorg", "name": "status-filter-repo"}
    repo = create_or_update_repository(
        db_session, meta, "https://github.com/testorg/status-filter-repo", user_id=override_current_user.id
    )

    # Completed run
    run_comp = create_analysis_run(db_session, repo.id, AnalysisType.DETERMINISTIC.value)
    run_comp.created_at = now - timedelta(hours=3)
    save_deterministic_results(db_session, run_comp.id, {
        "metrics": {"total_lines": 1000, "code_lines": 800},
        "summary": {"total_files": 10},
        "findings": []
    })
    mark_analysis_completed(db_session, run_comp.id)

    # Pending run
    run_pend = create_analysis_run(db_session, repo.id, AnalysisType.DETERMINISTIC.value)
    run_pend.created_at = now - timedelta(hours=2)

    # Running run
    run_run = create_analysis_run(db_session, repo.id, AnalysisType.AI.value)
    run_run.created_at = now - timedelta(hours=1)
    mark_analysis_running(db_session, run_run.id)

    # Failed run
    run_fail = create_analysis_run(db_session, repo.id, AnalysisType.DETERMINISTIC.value)
    run_fail.created_at = now
    mark_analysis_failed(db_session, run_fail.id, "Syntax error")

    db_session.commit()

    response = client.get(f"/api/repositories/{repo.id}/trends")
    assert response.status_code == 200
    data = response.json()
    assert data["total_runs_analyzed"] == 1
    assert len(data["trends"]) == 1
    assert data["trends"][0]["analysis_id"] == str(run_comp.id)


def test_get_trends_owner_access(db_session: Session, override_current_user: User):
    """Test repository owner can access trends successfully."""
    meta = {"owner": "testorg", "name": "owner-repo"}
    repo = create_or_update_repository(
        db_session, meta, "https://github.com/testorg/owner-repo", user_id=override_current_user.id
    )
    response = client.get(f"/api/repositories/{repo.id}/trends")
    assert response.status_code == 200


def test_get_trends_non_owner_returns_404(db_session: Session, override_current_user: User):
    """Test non-owner requesting another user's repository trends receives 404 (tenant isolation)."""
    other_user = User(
        id=uuid.uuid4(),
        github_user_id="9000009",
        github_login="other-developer",
        name="Other Dev",
        email="otherdev@devlens.local"
    )
    db_session.add(other_user)
    db_session.commit()

    meta = {"owner": "otherorg", "name": "private-repo"}
    other_repo = create_or_update_repository(
        db_session, meta, "https://github.com/otherorg/private-repo", user_id=other_user.id
    )

    response = client.get(f"/api/repositories/{other_repo.id}/trends")
    assert response.status_code == 404
    assert f"Repository '{other_repo.id}' not found" in response.json()["detail"]


def test_get_trends_missing_repository_returns_404():
    """Test non-existent repository UUID returns 404."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/repositories/{random_id}/trends")
    assert response.status_code == 404
    assert f"Repository '{random_id}' not found" in response.json()["detail"]


def test_get_trends_invalid_uuid_returns_404():
    """Test invalid repository ID string returns 404 without 500 error."""
    response = client.get("/api/repositories/invalid-not-a-uuid/trends")
    assert response.status_code == 404


@pytest.mark.unauthenticated
def test_get_trends_unauthenticated_returns_401():
    """Test unauthenticated request to /api/repositories/{id}/trends returns 401."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/repositories/{random_id}/trends")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]
