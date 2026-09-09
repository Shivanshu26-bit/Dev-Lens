import pytest
from pydantic import ValidationError
from app.models.ai_models import (
    AIAnalysisReport,
    ArchitectureAssessment,
    SecurityAssessment,
    PerformanceAssessment,
    MaintainabilityAssessment,
    DocumentationAssessment,
    PriorityRecommendation,
    AssessmentRating,
    PriorityLevel,
    ConfidenceLevel,
)


def valid_report_dict():
    return {
        "executive_summary": "Overall well-structured application with good separation of concerns.",
        "architecture": {
            "rating": "good",
            "assessment": "Modular architecture following clean separation.",
            "strengths": ["Clear service boundaries", "Typed models"],
            "weaknesses": ["Tight coupling in router"]
        },
        "security": {
            "rating": "needs_attention",
            "assessment": "Identified hardcoded credential risk.",
            "strengths": ["Input validation using Pydantic"],
            "weaknesses": ["Secrets in source files"],
            "important_issues": ["Hardcoded API key in config"],
            "recommendations": ["Use environment variables for credentials"]
        },
        "performance": {
            "rating": "good",
            "assessment": "Lightweight async operations.",
            "recommendations": ["Add caching for repeated lookups"]
        },
        "maintainability": {
            "rating": "excellent",
            "assessment": "High readability and type coverage.",
            "recommendations": ["Increase test coverage for edge cases"]
        },
        "documentation": {
            "rating": "fair",
            "assessment": "Basic README exists but lacks architecture diagrams.",
            "recommendations": ["Add API endpoint documentation"]
        },
        "strengths": [
            "Modular analyzer design",
            "Fast deterministic pipeline"
        ],
        "priorities": [
            {
                "priority": "critical",
                "category": "Security",
                "title": "Remediate Hardcoded API Key",
                "explanation": "Hardcoded keys can be extracted and abused.",
                "recommendation": "Remove credential and load from environment.",
                "evidence": "src/main.py: line 34"
            }
        ],
        "confidence": "high",
        "confidence_reason": None
    }


def test_valid_ai_analysis_report():
    data = valid_report_dict()
    report = AIAnalysisReport.model_validate(data)
    
    assert report.executive_summary.startswith("Overall")
    assert report.architecture.rating == AssessmentRating.GOOD
    assert report.security.rating == AssessmentRating.NEEDS_ATTENTION
    assert len(report.architecture.strengths) == 2
    assert len(report.priorities) == 1
    assert report.priorities[0].priority == PriorityLevel.CRITICAL
    assert report.confidence == ConfidenceLevel.HIGH


def test_invalid_rating_enum_raises_validation_error():
    data = valid_report_dict()
    data["architecture"]["rating"] = "super_awesome"  # Invalid enum
    
    with pytest.raises(ValidationError) as exc_info:
        AIAnalysisReport.model_validate(data)
    assert "architecture.rating" in str(exc_info.value)


def test_invalid_priority_enum_raises_validation_error():
    data = valid_report_dict()
    data["priorities"][0]["priority"] = "urgent"  # Invalid enum, must be critical/high/medium/low
    
    with pytest.raises(ValidationError) as exc_info:
        AIAnalysisReport.model_validate(data)
    assert "priorities.0.priority" in str(exc_info.value)


def test_invalid_confidence_enum_raises_validation_error():
    data = valid_report_dict()
    data["confidence"] = "very_high"  # Invalid enum
    
    with pytest.raises(ValidationError) as exc_info:
        AIAnalysisReport.model_validate(data)
    assert "confidence" in str(exc_info.value)


def test_missing_required_field_raises_validation_error():
    data = valid_report_dict()
    del data["executive_summary"]
    
    with pytest.raises(ValidationError) as exc_info:
        AIAnalysisReport.model_validate(data)
    assert "executive_summary" in str(exc_info.value)


def test_confidence_reason_optional():
    data = valid_report_dict()
    data["confidence"] = "medium"
    data["confidence_reason"] = "Only 3 source files available"
    
    report = AIAnalysisReport.model_validate(data)
    assert report.confidence == ConfidenceLevel.MEDIUM
    assert report.confidence_reason == "Only 3 source files available"
