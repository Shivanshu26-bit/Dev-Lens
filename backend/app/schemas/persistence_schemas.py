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


class LatestAnalysisSummary(BaseModel):
    """Schema representing an abbreviated summary of the latest analysis run for dashboard display."""
    id: uuid.UUID
    status: str
    analysis_type: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    total_lines: Optional[int] = None
    code_lines: Optional[int] = None
    total_files: Optional[int] = None
    findings_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class RepositoryListItemResponse(RepositoryResponse):
    """Schema for repository list items containing latest analysis run metadata."""
    latest_analysis: Optional[LatestAnalysisSummary] = None

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


class TrendPoint(BaseModel):
    """Schema representing a single historical analysis trend point with comparison deltas."""
    analysis_id: uuid.UUID
    analysis_type: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    total_lines: Optional[int] = None
    code_lines: Optional[int] = None
    total_files: Optional[int] = None
    findings_count: Optional[int] = None
    delta_total_lines: Optional[int] = None
    delta_code_lines: Optional[int] = None
    delta_total_files: Optional[int] = None
    delta_findings_count: Optional[int] = None
    pct_change_total_lines: Optional[float] = None
    pct_change_code_lines: Optional[float] = None
    pct_change_total_files: Optional[float] = None
    pct_change_findings_count: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class RepositoryTrendsResponse(BaseModel):
    """Schema representing the historical trends and comparison response for a repository."""
    repository_id: uuid.UUID
    github_url: str
    owner: str
    name: str
    total_runs_analyzed: int
    trends: List[TrendPoint]

    model_config = ConfigDict(from_attributes=True)
