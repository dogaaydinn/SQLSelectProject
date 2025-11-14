"""
Salary Pydantic Schemas
Data validation and serialization for Salary API
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class SalaryBase(BaseModel):
    """Base salary schema with common fields."""
    salary: Decimal = Field(..., gt=0, decimal_places=2, description="Base salary amount")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Currency code")
    from_date: date = Field(..., description="Salary effective from date")
    to_date: date = Field(default=date(9999, 12, 31), description="Salary effective to date")
    salary_type: str = Field(default="Base", max_length=50, description="Salary type")
    bonus: Optional[Decimal] = Field(
        default=Decimal(0), ge=0, decimal_places=2, description="Bonus amount"
    )
    commission: Optional[Decimal] = Field(
        default=Decimal(0), ge=0, decimal_places=2, description="Commission amount"
    )

    @field_validator("to_date")
    @classmethod
    def validate_to_date(cls, v, info):
        """Validate that to_date is after from_date."""
        if "from_date" in info.data and v < info.data["from_date"]:
            raise ValueError("to_date must be after from_date")
        return v


class SalaryCreate(SalaryBase):
    """Schema for creating a new salary record."""
    emp_no: int = Field(..., gt=0, description="Employee number")


class SalaryUpdate(BaseModel):
    """Schema for updating an existing salary record."""
    salary: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    salary_type: Optional[str] = Field(None, max_length=50)
    bonus: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    commission: Optional[Decimal] = Field(None, ge=0, decimal_places=2)


class SalaryResponse(SalaryBase):
    """Schema for salary response with metadata."""
    id: int
    emp_no: int
    uuid: str
    created_at: str
    updated_at: str
    version: int
    is_deleted: bool

    class Config:
        from_attributes = True


class SalaryWithEmployee(SalaryResponse):
    """Schema for salary response with employee information."""
    employee_name: str = Field(..., description="Employee full name")
    employee_email: Optional[str] = Field(None, description="Employee email")
