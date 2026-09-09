import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisRun, AnalysisStatus, AnalysisType


def _to_json_compatible(obj: Any) -> Any:
    """Converts Pydantic models or data structures into JSON-serializable primitives."""
    if obj is None:
        return None
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {k: _to_json_compatible(v) for k, v in obj.items() if k != "file_contents"}
    if isinstance(obj, list):
        return [_to_json_compatible(item) for item in obj]
    return obj


def create_analysis_run(
    db: Session,
    repository_id: Union[uuid.UUID, str],
    analysis_type: str = AnalysisType.DETERMINISTIC.value
) -> AnalysisRun:
    """
    Creates a new analysis run record in pending state.
    """
    if isinstance(repository_id, str):
        repository_id = uuid.UUID(repository_id)

    run = AnalysisRun(
        repository_id=repository_id,
        status=AnalysisStatus.PENDING.value,
        analysis_type=analysis_type,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def mark_analysis_running(
    db: Session,
    analysis_id: Union[uuid.UUID, str]
) -> Optional[AnalysisRun]:
    """
    Marks an analysis run as currently running.
    """
    run = get_analysis_by_id(db, analysis_id)
    if not run:
        return None

    run.status = AnalysisStatus.RUNNING.value
    run.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run


def save_deterministic_results(
    db: Session,
    analysis_id: Union[uuid.UUID, str],
    report_data: Union[Dict[str, Any], BaseModel]
) -> Optional[AnalysisRun]:
    """
    Saves Phase 3 deterministic analysis report and parsed sub-structures.
    """
    run = get_analysis_by_id(db, analysis_id)
    if not run:
        return None

    cleaned_data = _to_json_compatible(report_data)

    run.deterministic_result = cleaned_data
    if isinstance(cleaned_data, dict):
        run.metrics = cleaned_data.get("metrics")
        run.findings = cleaned_data.get("findings")
        run.languages = cleaned_data.get("languages")
        run.metadata_json = cleaned_data.get("analysis_metadata")

    db.commit()
    db.refresh(run)
    return run


def save_ai_results(
    db: Session,
    analysis_id: Union[uuid.UUID, str],
    ai_data: Union[Dict[str, Any], BaseModel]
) -> Optional[AnalysisRun]:
    """
    Saves Phase 4 Gemini AI analysis report.
    """
    run = get_analysis_by_id(db, analysis_id)
    if not run:
        return None

    run.ai_result = _to_json_compatible(ai_data)
    db.commit()
    db.refresh(run)
    return run


def mark_analysis_completed(
    db: Session,
    analysis_id: Union[uuid.UUID, str]
) -> Optional[AnalysisRun]:
    """
    Marks an analysis run as completed and records completion timestamp.
    """
    run = get_analysis_by_id(db, analysis_id)
    if not run:
        return None

    run.status = AnalysisStatus.COMPLETED.value
    run.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run


def mark_analysis_failed(
    db: Session,
    analysis_id: Union[uuid.UUID, str],
    error_message: str
) -> Optional[AnalysisRun]:
    """
    Marks an analysis run as failed and records the safe error message.
    """
    run = get_analysis_by_id(db, analysis_id)
    if not run:
        return None

    run.status = AnalysisStatus.FAILED.value
    run.completed_at = datetime.now(timezone.utc)
    run.error_message = error_message
    db.commit()
    db.refresh(run)
    return run


def get_analysis_by_id(
    db: Session,
    analysis_id: Union[uuid.UUID, str],
    user_id: Optional[Union[uuid.UUID, str]] = None
) -> Optional[AnalysisRun]:
    """
    Retrieves an analysis run record by its UUID primary key.
    If user_id is supplied, enforces that the parent repository belongs to user_id.
    """
    if isinstance(analysis_id, str):
        try:
            analysis_id = uuid.UUID(analysis_id)
        except ValueError:
            return None

    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except ValueError:
            return None

    stmt = select(AnalysisRun).where(AnalysisRun.id == analysis_id)
    run = db.scalars(stmt).first()
    if not run:
        return None

    if user_id is not None:
        if run.repository is None or run.repository.user_id != user_id:
            return None

    return run


def get_analyses_by_repository(
    db: Session,
    repository_id: Union[uuid.UUID, str],
    user_id: Optional[Union[uuid.UUID, str]] = None,
    limit: int = 20
) -> List[AnalysisRun]:
    """
    Retrieves the historical analysis runs for a given repository ordered by creation date desc.
    If user_id is supplied, verifies that the repository belongs to user_id.
    """
    if isinstance(repository_id, str):
        try:
            repository_id = uuid.UUID(repository_id)
        except ValueError:
            return []

    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except ValueError:
            return []

    if user_id is not None:
        from app.services.repository_persistence import get_repository_by_id
        repo = get_repository_by_id(db, repository_id, user_id=user_id)
        if not repo:
            return []

    stmt = (
        select(AnalysisRun)
        .where(AnalysisRun.repository_id == repository_id)
        .order_by(desc(AnalysisRun.created_at), desc(AnalysisRun.id))
        .limit(limit)
    )
    return list(db.scalars(stmt).all())
