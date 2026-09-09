from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class AssessmentRating(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    NEEDS_ATTENTION = "needs_attention"
    POOR = "poor"


class PriorityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ArchitectureAssessment(BaseModel):
    rating: AssessmentRating = Field(..., description="Categorical architectural assessment rating")
    assessment: str = Field(..., description="Detailed narrative assessment of the codebase architecture")
    strengths: List[str] = Field(default_factory=list, description="Architectural strengths observed")
    weaknesses: List[str] = Field(default_factory=list, description="Architectural weaknesses or technical debt")


class SecurityAssessment(BaseModel):
    rating: AssessmentRating = Field(..., description="Categorical security assessment rating")
    assessment: str = Field(..., description="Detailed narrative evaluation of the repository security posture")
    strengths: List[str] = Field(default_factory=list, description="Positive security practices identified")
    weaknesses: List[str] = Field(default_factory=list, description="Identified security gaps or weaknesses")
    important_issues: List[str] = Field(default_factory=list, description="Important security findings or concerns")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations for hardening")


class PerformanceAssessment(BaseModel):
    rating: AssessmentRating = Field(..., description="Categorical performance assessment rating")
    assessment: str = Field(..., description="Evaluation of algorithmic efficiency, scalability, and resource usage")
    recommendations: List[str] = Field(default_factory=list, description="Performance optimization recommendations")


class MaintainabilityAssessment(BaseModel):
    rating: AssessmentRating = Field(..., description="Categorical maintainability assessment rating")
    assessment: str = Field(..., description="Evaluation of code readability, modularity, and testability")
    recommendations: List[str] = Field(default_factory=list, description="Maintainability improvement recommendations")


class DocumentationAssessment(BaseModel):
    rating: AssessmentRating = Field(..., description="Categorical documentation assessment rating")
    assessment: str = Field(..., description="Evaluation of README, API docs, inline comments, and setup guides")
    recommendations: List[str] = Field(default_factory=list, description="Documentation enhancement recommendations")


class PriorityRecommendation(BaseModel):
    priority: PriorityLevel = Field(..., description="Severity or urgency of the recommendation")
    category: str = Field(..., description="Domain category (e.g. Architecture, Security, Performance, Testing)")
    title: str = Field(..., description="Concise, actionable recommendation title")
    explanation: str = Field(..., description="Rationale for why this improvement matters")
    recommendation: str = Field(..., description="Specific implementation steps to resolve")
    evidence: str = Field(..., description="Specific files, functions, or patterns supporting this recommendation")


class AIAnalysisReport(BaseModel):
    executive_summary: str = Field(..., description="Concise AI engineering executive summary")
    architecture: ArchitectureAssessment = Field(..., description="Architecture review")
    security: SecurityAssessment = Field(..., description="Security review")
    performance: PerformanceAssessment = Field(..., description="Performance review")
    maintainability: MaintainabilityAssessment = Field(..., description="Maintainability review")
    documentation: DocumentationAssessment = Field(..., description="Documentation review")
    strengths: List[str] = Field(default_factory=list, description="General engineering strengths observed")
    priorities: List[PriorityRecommendation] = Field(default_factory=list, description="Ordered priority recommendations")
    confidence: ConfidenceLevel = Field(..., description="Confidence level of the assessment based on available evidence")
    confidence_reason: Optional[str] = Field(default=None, description="Explanation when confidence is medium or low")
