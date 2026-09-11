import logging
from typing import Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """
    Extracts client IP address, supporting reverse proxies (e.g. Render, Cloudflare)
    by prioritizing the first address in X-Forwarded-For before request.client.host.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


def get_rate_limit_key(request: Request) -> str:
    """
    Determines rate limit identity key:
    1. Authenticated user session (via HttpOnly session cookie) -> "sess:<token>"
    2. Unauthenticated client -> "ip:<client_ip>"
    """
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if token:
        return f"sess:{token}"

    return f"ip:{get_client_ip(request)}"


def get_storage_uri() -> str:
    """
    Resolves storage backend URI for rate limiting:
    - If RATE_LIMIT_STORAGE_URL is configured, use it.
    - Else if REDIS_URL is configured, use it.
    - Defaults to 'memory://' for local development and single-worker deployments.
    """
    if settings.RATE_LIMIT_STORAGE_URL and settings.RATE_LIMIT_STORAGE_URL.strip():
        return settings.RATE_LIMIT_STORAGE_URL.strip()
    if settings.REDIS_URL and settings.REDIS_URL.strip():
        return settings.REDIS_URL.strip()
    return "memory://"


def create_limiter() -> Limiter:
    """
    Creates and configures the SlowAPI Limiter instance.
    Supports shared Redis storage for multi-worker/multi-instance deployments on Render,
    with automatic in-memory fallback and fail-open error swallowing to guarantee application uptime.
    """
    storage_uri = get_storage_uri()
    if storage_uri.startswith("redis"):
        # Log sanitized destination without exposing credentials
        sanitized = storage_uri.split("@")[-1] if "@" in storage_uri else storage_uri
        logger.info("Initializing rate limiter with shared Redis backend: %s", sanitized)
    else:
        logger.info("Initializing rate limiter with in-memory storage backend")

    return Limiter(
        key_func=get_rate_limit_key,
        storage_uri=storage_uri,
        enabled=settings.RATE_LIMIT_ENABLED,
        in_memory_fallback_enabled=True,
        swallow_errors=True,
        headers_enabled=False,
    )


limiter = create_limiter()


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom HTTP 429 Too Many Requests exception handler returning standardized JSON
    with Retry-After header.
    """
    logger.warning(
        "Rate limit exceeded on %s %s [key: %s]: %s",
        request.method,
        request.url.path,
        get_rate_limit_key(request),
        exc.detail
    )
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": f"Rate limit exceeded: {exc.detail}. Please try again later."
        },
        headers={"Retry-After": "60"}
    )
