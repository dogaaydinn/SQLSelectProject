"""
API v1 Router
"""

from fastapi import APIRouter
from app.api.v1.endpoints import employees, departments, salaries, analytics, health

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(employees.router, prefix="/employees", tags=["Employees"])
api_router.include_router(departments.router, prefix="/departments", tags=["Departments"])
api_router.include_router(salaries.router, prefix="/salaries", tags=["Salaries"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
