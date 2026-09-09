from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.analysis import AnalysisType
from app.schemas.persistence_schemas import RepositoryResponse, AnalysisRunSummaryResponse
from app.services.repository_persistence import (
    create_or_update_repository,
    get_repository_by_id,
    update_last_analyzed
)
from app.services.analysis_persistence import (
    create_analysis_run,
    mark_analysis_running,
    save_deterministic_results,
    save_ai_results,
    mark_analysis_completed,
    mark_analysis_failed,
    get_analyses_by_repository
)
from app.services.github_url import parse_github_url
from app.services.github_service import (
    GitHubService,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubAPIError
)

from app.analyzers.repository_analyzer import analyze_repository as run_repo_analysis
from app.models.ai_models import AIAnalysisReport
from app.analyzers.evidence_selector import EvidenceSelector
from app.services.ai_service import (
    AIService,
    AIConfigError,
    AIRateLimitError,
    AITimeoutError,
    AIResponseValidationError,
    AIUnavailableError,
    AIServiceError
)

router = APIRouter(prefix="/api/repositories", tags=["repositories"])

class AnalyzeRequest(BaseModel):
    url: str = Field(..., description="The GitHub repository URL to ingest (e.g. https://github.com/owner/repo)")

class RepositoryMetadata(BaseModel):
    owner: str
    name: str
    full_name: str
    description: Optional[str] = None
    default_branch: str
    language: Optional[str] = None
    stars: int
    forks: int
    open_issues: int
    url: str

class TreeItem(BaseModel):
    path: str
    type: str  # "file" or "directory"

class AnalyzeResponse(BaseModel):
    repository: RepositoryMetadata
    tree: List[TreeItem]

# Phase 3 Analysis Report Schemas
class AnalysisSummary(BaseModel):
    total_files: int
    analyzed_files: int
    skipped_files: int
    source_files: int
    test_files: int
    documentation_files: int
    configuration_files: int
    asset_files: int
    unknown_files: int

class LanguageDistribution(BaseModel):
    language: str
    file_count: int
    percentage: float

class FileMetrics(BaseModel):
    path: str
    language: str
    category: str
    size_bytes: int
    line_count: int
    code_lines: int
    comment_lines: int
    blank_lines: int

class SizeMetric(BaseModel):
    path: str
    size_bytes: int

class LinesMetric(BaseModel):
    path: str
    line_count: int

class RepoMetrics(BaseModel):
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    largest_files_by_size: List[SizeMetric]
    largest_files_by_lines: List[LinesMetric]

class Finding(BaseModel):
    id: str
    severity: str
    category: str
    title: str
    description: str
    file: str
    line: int
    recommendation: str

class AnalysisMetadata(BaseModel):
    files_analyzed: int
    files_skipped: int
    skip_reasons: dict

class AnalysisReport(BaseModel):
    repository: RepositoryMetadata
    summary: AnalysisSummary
    languages: List[LanguageDistribution]
    files: List[FileMetrics]
    metrics: RepoMetrics
    findings: List[Finding]
    analysis_metadata: AnalysisMetadata
    tree: List[TreeItem]

# Phase 4 AI Analysis Response Schema
class AIAnalyzeResponse(BaseModel):
    repository: RepositoryMetadata
    deterministic_analysis: AnalysisReport
    ai_analysis: AIAnalysisReport


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_repository(payload: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    Ingests a public GitHub repository, validating its URL, retrieving
    its metadata, and fetching its repository tree structure.
    """
    # 1. Parse and validate GitHub URL
    try:
        owner, repo = parse_github_url(payload.url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    # 2. Fetch data from GitHub API service
    github_service = GitHubService()
    try:
        metadata = await github_service.get_repo_metadata(owner, repo)
        
        branch = metadata.get("default_branch", "main")
        tree_items = await github_service.get_repo_tree(owner, repo, branch)
        
        # Persist repository metadata
        create_or_update_repository(db, metadata, payload.url)

        # 3. Format response schemas
        repo_metadata = RepositoryMetadata(
            owner=metadata["owner"],
            name=metadata["name"],
            full_name=metadata["full_name"],
            description=metadata["description"],
            default_branch=metadata["default_branch"],
            language=metadata["language"],
            stars=metadata["stars"],
            forks=metadata["forks"],
            open_issues=metadata["open_issues"],
            url=metadata["url"]
        )
        
        formatted_tree = [
            TreeItem(path=item["path"], type=item["type"])
            for item in tree_items
        ]
        
        return AnalyzeResponse(
            repository=repo_metadata,
            tree=formatted_tree
        )
        
    except GitHubNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except GitHubRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except GitHubAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )

@router.post("/analyze/report", response_model=AnalysisReport)
async def analyze_repository_report(payload: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    Runs the full static analysis engine on a public GitHub repository
    and returns a structured engineering report.
    """
    # 1. Parse and validate GitHub URL
    try:
        owner, repo = parse_github_url(payload.url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    # 2. Fetch repo tree and metadata, then run static analysis engine
    github_service = GitHubService()
    try:
        metadata = await github_service.get_repo_metadata(owner, repo)
        
        branch = metadata.get("default_branch", "main")
        tree_items = await github_service.get_repo_tree(owner, repo, branch)
        
        repo_record = create_or_update_repository(db, metadata, payload.url)
        run_record = create_analysis_run(db, repo_record.id, AnalysisType.DETERMINISTIC.value)
        mark_analysis_running(db, run_record.id)

        try:
            # Invoke central static analysis report engine
            report = await run_repo_analysis(owner, repo, metadata, tree_items)
            save_deterministic_results(db, run_record.id, report)
            mark_analysis_completed(db, run_record.id)
            update_last_analyzed(db, repo_record.id)
            return report
        except Exception as err:
            mark_analysis_failed(db, run_record.id, str(err))
            raise
        
    except GitHubNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except GitHubRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except GitHubAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )


@router.post("/analyze/ai", response_model=AIAnalyzeResponse)
async def analyze_repository_ai(payload: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    Ingests a public GitHub repository, executes deterministic Phase 3 static analysis,
    selects prioritized code evidence with secret redaction, and invokes the Gemini AI
    intelligence layer to return a validated engineering assessment.
    """
    # 1. Parse and validate GitHub URL
    try:
        owner, repo = parse_github_url(payload.url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # 2. Fetch repo tree and metadata from GitHub
    github_service = GitHubService()
    try:
        metadata = await github_service.get_repo_metadata(owner, repo)
        branch = metadata.get("default_branch", "main")
        tree_items = await github_service.get_repo_tree(owner, repo, branch)

        repo_record = create_or_update_repository(db, metadata, payload.url)
        run_record = create_analysis_run(db, repo_record.id, AnalysisType.AI.value)
        mark_analysis_running(db, run_record.id)

        try:
            # 3. Run deterministic Phase 3 static analysis
            deterministic_dict = await run_repo_analysis(owner, repo, metadata, tree_items)
            save_deterministic_results(db, run_record.id, deterministic_dict)
            cached_contents = deterministic_dict.get("file_contents", {})

            # 4. Select and redact evidence for AI review
            selector = EvidenceSelector()
            evidence_bundle = await selector.select_evidence(
                deterministic_report=deterministic_dict,
                owner=owner,
                repo=repo,
                default_branch=branch,
                github_service=github_service,
                cached_file_contents=cached_contents
            )

            # 5. Invoke Gemini AI Service
            ai_service = AIService()
            ai_analysis = await ai_service.analyze_repository(evidence_bundle)
            save_ai_results(db, run_record.id, ai_analysis)

            mark_analysis_completed(db, run_record.id)
            update_last_analyzed(db, repo_record.id)

            # 6. Format and return response
            deterministic_report = AnalysisReport(**deterministic_dict)
            return AIAnalyzeResponse(
                repository=deterministic_report.repository,
                deterministic_analysis=deterministic_report,
                ai_analysis=ai_analysis
            )
        except Exception as err:
            mark_analysis_failed(db, run_record.id, str(err))
            raise

    except GitHubNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except GitHubRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except GitHubAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )
    except AIConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except AIRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except AITimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e)
        )
    except AIResponseValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI assessment response validation failed: {str(e)}"
        )
    except (AIUnavailableError, AIServiceError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analysis is temporarily unavailable. Please try again."
        )


@router.get("/{repository_id}", response_model=RepositoryResponse)
def get_repository(repository_id: str, db: Session = Depends(get_db)):
    """
    Retrieves a persisted repository record by its UUID primary key.
    """
    repo = get_repository_by_id(db, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repository_id}' not found"
        )
    return repo


@router.get("/{repository_id}/analyses", response_model=List[AnalysisRunSummaryResponse])
def get_repository_analyses(repository_id: str, limit: int = 20, db: Session = Depends(get_db)):
    """
    Retrieves historical analysis runs for a repository, ordered by creation date desc.
    """
    repo = get_repository_by_id(db, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repository_id}' not found"
        )
    return get_analyses_by_repository(db, repository_id, limit=limit)


