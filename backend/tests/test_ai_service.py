import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from google.genai.errors import APIError

from app.services.ai_service import (
    AIService,
    AIConfigError,
    AIRateLimitError,
    AITimeoutError,
    AIResponseValidationError,
    AIUnavailableError,
)
from app.models.ai_models import AIAnalysisReport, AssessmentRating, PriorityLevel, ConfidenceLevel

pytestmark = pytest.mark.anyio


def sample_valid_ai_json():
    return json.dumps({
        "executive_summary": "Architecture is modular with good design.",
        "architecture": {
            "rating": "good",
            "assessment": "Clear layers and separation.",
            "strengths": ["Clean routers"],
            "weaknesses": []
        },
        "security": {
            "rating": "good",
            "assessment": "No critical vulnerabilities found.",
            "strengths": ["Input sanitization"],
            "weaknesses": [],
            "important_issues": [],
            "recommendations": ["Add security headers"]
        },
        "performance": {
            "rating": "excellent",
            "assessment": "High-throughput async design.",
            "recommendations": []
        },
        "maintainability": {
            "rating": "good",
            "assessment": "Readable codebase.",
            "recommendations": []
        },
        "documentation": {
            "rating": "fair",
            "assessment": "Standard documentation.",
            "recommendations": ["Expand docstrings"]
        },
        "strengths": ["Strong typing"],
        "priorities": [
            {
                "priority": "medium",
                "category": "Documentation",
                "title": "Document API endpoints",
                "explanation": "Clearer docs improve developer onboarding.",
                "recommendation": "Add OpenAPI schema tags.",
                "evidence": "app/main.py"
            }
        ],
        "confidence": "high",
        "confidence_reason": None
    })


async def test_missing_api_key_raises_config_error():
    service = AIService(api_key="")
    with pytest.raises(AIConfigError) as exc:
        await service.analyze_repository({})
    assert "Gemini API key is not configured" in str(exc.value)


async def test_successful_ai_response_parsing():
    service = AIService(api_key="fake-test-key")
    
    mock_response = MagicMock()
    mock_response.text = sample_valid_ai_json()

    with patch("app.services.ai_service.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        report = await service.analyze_repository({"repository": {"name": "test"}})

        assert isinstance(report, AIAnalysisReport)
        assert report.architecture.rating == AssessmentRating.GOOD
        assert report.confidence == ConfidenceLevel.HIGH
        assert len(report.priorities) == 1
        assert report.priorities[0].priority == PriorityLevel.MEDIUM


async def test_api_rate_limit_error_handling():
    service = AIService(api_key="fake-test-key")

    with patch("app.services.ai_service.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        # Simulate 429 / RESOURCE_EXHAUSTED
        api_err = APIError(429, "Resource has been exhausted (e.g. check quota).")
        api_err.code = 429
        mock_client.aio.models.generate_content = AsyncMock(side_effect=api_err)
        mock_client_cls.return_value = mock_client

        with pytest.raises(AIRateLimitError) as exc:
            await service.analyze_repository({})
        assert "rate limit" in str(exc.value).lower()


async def test_timeout_error_handling():
    service = AIService(api_key="fake-test-key", timeout=0.01)

    async def slow_generate(*args, **kwargs):
        await asyncio.sleep(0.1)
        return MagicMock()

    with patch("app.services.ai_service.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(side_effect=slow_generate)
        mock_client_cls.return_value = mock_client

        with pytest.raises(AITimeoutError) as exc:
            await service.analyze_repository({})
        assert "timed out" in str(exc.value).lower()


async def test_malformed_response_raises_validation_error():
    service = AIService(api_key="fake-test-key")

    mock_response = MagicMock()
    mock_response.text = "This is plain text, not JSON at all."

    with patch("app.services.ai_service.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        with pytest.raises(AIResponseValidationError) as exc:
            await service.analyze_repository({})
        assert "validation failed" in str(exc.value).lower()


async def test_schema_validation_failure():
    service = AIService(api_key="fake-test-key")

    # Missing mandatory fields
    bad_json = json.dumps({"executive_summary": "Incomplete data"})
    mock_response = MagicMock()
    mock_response.text = bad_json

    with patch("app.services.ai_service.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        with pytest.raises(AIResponseValidationError) as exc:
            await service.analyze_repository({})
        assert "validation failed" in str(exc.value).lower()
