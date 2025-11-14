"""
Salary API Endpoints
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_salaries():
    """List salaries."""
    return {"message": "Salary endpoints - Implementation in progress"}
