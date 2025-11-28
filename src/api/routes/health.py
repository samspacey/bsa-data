"""Health check endpoints."""

from fastapi import APIRouter

from src.config.settings import settings
from src.data.database import get_engine, get_session
from src.data.models import PublicReview

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Basic health check.

    Returns:
        Health status
    """
    return {"status": "healthy"}


@router.get("/health/detailed")
async def detailed_health_check() -> dict:
    """Detailed health check with database stats.

    Returns:
        Detailed health status
    """
    try:
        engine = get_engine()
        with get_session(engine) as session:
            review_count = session.query(PublicReview).count()

        return {
            "status": "healthy",
            "database": {
                "connected": True,
                "path": str(settings.sqlite_db_path),
                "review_count": review_count,
            },
            "vector_index": {
                "path": str(settings.lancedb_path),
            },
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
