from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

from app.api.repositories import router as repositories_router
from app.api.analyses import router as analyses_router
from app.api.auth import router as auth_router

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
def health_check():
    """
    Health check endpoint to verify backend api status.
    """
    return {
        "status": "ok",
        "project": settings.PROJECT_NAME,
        "features": {
            "database_integrated": False,
            "ai_analysis_integrated": False
        }
    }
