import logging
from fastapi import FastAPI, Response, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.api.repositories import router as repositories_router
from app.api.analyses import router as analyses_router
from app.api.auth import router as auth_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="DevLens — AI-powered GitHub repository analysis platform backend",
    version="0.1.0"
)

# Register routers
app.include_router(auth_router)
app.include_router(repositories_router)
app.include_router(analyses_router)

# CORS middleware configuration
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/health", status_code=200)
def health_check(response: Response, db: Session = Depends(get_db)):
    """
    Health check endpoint that verifies API status and database reachability.
    Returns HTTP 200 when database is reachable, or HTTP 503 when unreachable.
    """
    db_connected = False
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if db_connected else "unhealthy",
        "project": settings.PROJECT_NAME,
        "database": "connected" if db_connected else "disconnected",
        "features": {
            "database_integrated": db_connected,
            "ai_analysis_integrated": bool(settings.GEMINI_API_KEY)
        }
    }
