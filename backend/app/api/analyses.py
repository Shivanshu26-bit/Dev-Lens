from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.api.auth import get_current_user
from app.schemas.persistence_schemas import AnalysisRunResponse
from app.services.analysis_persistence import get_analysis_by_id

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


@router.get("/{analysis_id}", response_model=AnalysisRunResponse)
def get_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves the complete persisted record and payloads of an analysis run by UUID.
    Enforces user ownership and returns 404 if not found or unauthorized.
    """
    run = get_analysis_by_id(db, analysis_id, user_id=current_user.id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis run '{analysis_id}' not found"
        )
    return run
