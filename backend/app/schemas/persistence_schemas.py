import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict


class RepositoryResponse(BaseModel):
    """Schema representing persisted repository details."""
    id: uuid.UUID
    github_url: str
    owner: str
    name: str
    default_branch: Optional[str] = "main"
    description: Optional[str] = None
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    language: Optional[str] = None
    is_private: bool = False
    created_at: datetime
    updated_at: datetime
    last_analyzed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AnalysisRunSummaryResponse(BaseModel):
    """Schema representing an abbreviated summary of an analysis run."""
    id: uuid.UUID
    repository_id: uuid.UUID
    status: str
    analysis_type: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AnalysisRunResponse(AnalysisRunSummaryResponse):
    """Schema representing full details and JSON payloads of an analysis run."""
    deterministic_result: Optional[Dict[str, Any]] = None
    ai_result: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    findings: Optional[List[Dict[str, Any]]] = None
    languages: Optional[List[Dict[str, Any]]] = None
    metadata_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
