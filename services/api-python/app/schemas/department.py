"""
Department Pydantic Schemas
Data validation and serialization for Department API
"""

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class DepartmentBase(BaseModel):
    """Base department schema with common fields."""
    dept_name: str = Field(..., min_length=1, max_length=100, description="Department name")
    description: Optional[str] = Field(None, description="Department description")
    manager_emp_no: Optional[int] = Field(None, description="Manager employee number")
    budget: Optional[Decimal] = Field(None, description="Department budget")
    location: Optional[str] = Field(None, description="Department location")
    is_active: bool = Field(True, description="Department active status")


class DepartmentCreate(DepartmentBase):
    """Schema for creating a new department."""
    dept_no: str = Field(
        ...,
        min_length=4,
        max_length=4,
        pattern=r"^d\d{3}$",
        description="Department number (format: d###)",
    )


class DepartmentUpdate(BaseModel):
    """Schema for updating an existing department."""
    dept_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    manager_emp_no: Optional[int] = None
    budget: Optional[Decimal] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentResponse(DepartmentBase):
    """Schema for department response with metadata."""
    dept_no: str
    uuid: str
    created_at: str
    updated_at: str
    version: int
    is_deleted: bool

    class Config:
        from_attributes = True


class DepartmentStatistics(BaseModel):
    """Schema for department statistics."""
    dept_no: str = Field(..., description="Department number")
    dept_name: str = Field(..., description="Department name")
    employee_count: int = Field(..., description="Number of employees")
    avg_salary: Optional[Decimal] = Field(None, description="Average salary")
    budget: Optional[Decimal] = Field(None, description="Department budget")
    budget_utilization: Optional[float] = Field(None, description="Budget utilization percentage")
    avg_tenure_days: Optional[float] = Field(None, description="Average employee tenure in days")
