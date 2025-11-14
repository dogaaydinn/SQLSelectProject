"""
Health Check Endpoints
"""

from fastapi import APIRouter, status
from app.core.database import DatabaseHealthCheck
from app.utils.cache import cache_manager

router = APIRouter()


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "service": "Employee Management API",
    }


@router.get("/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check():
    """Detailed health check with dependencies."""
    db_health = await DatabaseHealthCheck.check()
    cache_health = {
        "status": "healthy" if cache_manager.enabled and cache_manager.redis else "disabled",
        "enabled": cache_manager.enabled,
    }

    overall_status = "healthy" if db_health["status"] == "healthy" else "unhealthy"

    return {
        "status": overall_status,
        "service": "Employee Management API",
        "database": db_health,
        "cache": cache_health,
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """Readiness probe for Kubernetes."""
    db_health = await DatabaseHealthCheck.check()

    if db_health["status"] != "healthy":
        return {"status": "not_ready", "reason": "database_unavailable"}

    return {"status": "ready"}


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """Liveness probe for Kubernetes."""
    return {"status": "alive"}
