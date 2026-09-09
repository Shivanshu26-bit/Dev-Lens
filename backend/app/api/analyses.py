from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.persistence_schemas import AnalysisRunResponse
from app.services.analysis_persistence import get_analysis_by_id

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


@router.get("/{analysis_id}", response_model=AnalysisRunResponse)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the complete persisted record and payloads of an analysis run by UUID.
    """
    run = get_analysis_by_id(db, analysis_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis run '{analysis_id}' not found"
        )
    return run
