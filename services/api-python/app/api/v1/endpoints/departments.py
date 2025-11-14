"""
Department API Endpoints
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_departments():
    """List all departments."""
    return {"message": "Department endpoints - Implementation in progress"}


@router.get("/{dept_no}")
async def get_department(dept_no: str):
    """Get department by ID."""
    return {"dept_no": dept_no, "message": "Implementation in progress"}
