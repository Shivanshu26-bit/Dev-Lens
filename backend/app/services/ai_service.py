import asyncio
import json
import logging
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import ValidationError

from app.core.config import settings
from app.models.ai_models import AIAnalysisReport
from app.services.ai_prompts import SYSTEM_INSTRUCTION, build_analysis_prompt

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Base exception for all AI service errors."""
    pass


class AIConfigError(AIServiceError):
    """Raised when the AI service is misconfigured or API key is missing/invalid."""
    pass


class AIRateLimitError(AIServiceError):
    """Raised when Gemini API rate limit or quota is exceeded."""
    pass


class AITimeoutError(AIServiceError):
    """Raised when the AI request exceeds the configured timeout."""
    pass


class AIResponseValidationError(AIServiceError):
    """Raised when the AI response does not conform to the expected Pydantic schema."""
    pass


class AIUnavailableError(AIServiceError):
    """Raised when the Gemini API service is temporarily unavailable."""
    pass


def _clean_json_text(text: str) -> str:
    """Strips markdown code fences from raw LLM text if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


class AIService:
    """
    Client wrapper for Google Gemini AI that manages structured prompts,
    schema-enforced output generation, validation against Pydantic models,
    and application-level error translation.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.timeout = timeout or settings.AI_REQUEST_TIMEOUT_SECONDS

    def _get_client(self) -> genai.Client:
        """Initializes and returns the Google GenAI client."""
        if not self.api_key or not self.api_key.strip():
            raise AIConfigError("Gemini API key is not configured. Please set GEMINI_API_KEY in backend/.env")
        return genai.Client(api_key=self.api_key.strip())

    async def analyze_repository(self, evidence_bundle: Dict[str, Any]) -> AIAnalysisReport:
        """
        Submits repository evidence to Gemini and returns a validated AIAnalysisReport.

        Args:
            evidence_bundle: Formatted evidence bundle produced by EvidenceSelector.

        Returns:
            Validated AIAnalysisReport Pydantic instance.

        Raises:
            AIConfigError: If API key is missing or invalid.
            AIRateLimitError: If rate limit is exceeded.
            AITimeoutError: If generation times out.
            AIResponseValidationError: If output does not match Pydantic schema.
            AIUnavailableError: If Gemini service is unreachable.
        """
        client = self._get_client()
        user_prompt = build_analysis_prompt(evidence_bundle)

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AIAnalysisReport,
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,
        )

        try:
            logger.info("Submitting repository evidence to Gemini model: %s", self.model)
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=config
                ),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.error("Gemini AI request timed out after %.1f seconds", self.timeout)
            raise AITimeoutError(f"AI analysis timed out after {self.timeout} seconds. Please try again.")
        except APIError as e:
            err_msg = str(e).lower()
            status_code = getattr(e, "code", None)
            logger.error("Gemini API error (code: %s): %s", status_code, err_msg)

            if status_code == 429 or "resource_exhausted" in err_msg or "rate limit" in err_msg:
                raise AIRateLimitError("Gemini API rate limit exceeded. Please wait a moment and try again.")
            elif status_code in (400, 401, 403) and ("api_key_invalid" in err_msg or "permission_denied" in err_msg or "invalid api key" in err_msg):
                raise AIConfigError("Configured Gemini API key is invalid or unauthorized.")
            elif status_code in (500, 502, 503, 504) or "unavailable" in err_msg:
                raise AIUnavailableError("Gemini AI service is temporarily unavailable. Please try again shortly.")
            else:
                raise AIUnavailableError(f"Gemini API request failed: {status_code or 'unknown'}")
        except Exception as e:
            logger.exception("Unexpected error communicating with Gemini API: %s", str(e))
            raise AIServiceError(f"Unexpected error communicating with AI service: {str(e)}")

        # Parse and validate structured output
        raw_text = getattr(response, "text", None)
        if not raw_text:
            logger.error("Gemini returned empty response text")
            raise AIResponseValidationError("Gemini returned an empty response body.")

        cleaned_json = _clean_json_text(raw_text)

        try:
            report = AIAnalysisReport.model_validate_json(cleaned_json)
            logger.info("Successfully validated AIAnalysisReport from Gemini")
            return report
        except (ValidationError, json.JSONDecodeError) as val_err:
            logger.error("AI response schema validation failed: %s", str(val_err))
            raise AIResponseValidationError(f"AI response validation failed against schema: {str(val_err)}")
