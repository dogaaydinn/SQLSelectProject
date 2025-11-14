"""
Employee Pydantic Schemas
Request/Response validation models
"""

from datetime import date, datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, UUID4, field_validator
from enum import Enum


class GenderEnum(str, Enum):
    """Gender enumeration."""
    MALE = "M"
    FEMALE = "F"
    OTHER = "Other"
    PREFER_NOT_TO_SAY = "PreferNotToSay"


class EmploymentStatusEnum(str, Enum):
    """Employment status enumeration."""
    ACTIVE = "Active"
    TERMINATED = "Terminated"
    ON_LEAVE = "OnLeave"
    SUSPENDED = "Suspended"


# ============================================
# BASE SCHEMAS
# ============================================

class EmployeeBase(BaseModel):
    """Base employee schema."""
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    middle_name: Optional[str] = Field(None, max_length=50)
    birth_date: date
    gender: GenderEnum = GenderEnum.PREFER_NOT_TO_SAY
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: str = Field("USA", max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, v: date) -> date:
        """Validate birth date is reasonable."""
        if v.year < 1930:
            raise ValueError("Birth date must be after 1930")
        if v > date.today():
            raise ValueError("Birth date cannot be in the future")
        return v


class EmployeeCreate(EmployeeBase):
    """Schema for creating employee."""
    hire_date: date
    status: EmploymentStatusEnum = EmploymentStatusEnum.ACTIVE

    @field_validator("hire_date")
    @classmethod
    def validate_hire_date(cls, v: date) -> date:
        """Validate hire date."""
        if v.year < 1980:
            raise ValueError("Hire date must be after 1980")
        return v


class EmployeeUpdate(BaseModel):
    """Schema for updating employee."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    middle_name: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    status: Optional[EmploymentStatusEnum] = None
    termination_date: Optional[date] = None


class EmployeeInDB(EmployeeBase):
    """Employee as stored in database."""
    emp_no: int
    uuid: UUID4
    hire_date: date
    termination_date: Optional[date] = None
    status: EmploymentStatusEnum
    ssn_encrypted: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    version: int
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class EmployeeResponse(BaseModel):
    """Employee response schema."""
    emp_no: int
    uuid: UUID4
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    full_name: str
    birth_date: date
    age: int
    gender: GenderEnum
    hire_date: date
    years_of_service: float
    termination_date: Optional[date] = None
    status: EmploymentStatusEnum
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str
    current_salary: Optional[float] = None
    current_department: Optional[str] = None
    current_title: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================
# DEPARTMENT SCHEMAS
# ============================================

class DepartmentBase(BaseModel):
    """Base department schema."""
    dept_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    budget: Optional[float] = Field(None, ge=0)
    manager_emp_no: Optional[int] = None


class DepartmentCreate(DepartmentBase):
    """Schema for creating department."""
    dept_no: str = Field(..., min_length=4, max_length=4)


class DepartmentUpdate(BaseModel):
    """Schema for updating department."""
    dept_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    budget: Optional[float] = Field(None, ge=0)
    manager_emp_no: Optional[int] = None
    is_active: Optional[bool] = None


class DepartmentResponse(DepartmentBase):
    """Department response schema."""
    dept_no: str
    uuid: UUID4
    is_active: bool
    employee_count: Optional[int] = 0
    avg_salary: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================
# SALARY SCHEMAS
# ============================================

class SalaryBase(BaseModel):
    """Base salary schema."""
    salary: float = Field(..., gt=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    salary_type: str = Field("Base", max_length=50)
    bonus: float = Field(0, ge=0)
    commission: float = Field(0, ge=0)


class SalaryCreate(SalaryBase):
    """Schema for creating salary record."""
    emp_no: int
    from_date: date


class SalaryUpdate(BaseModel):
    """Schema for updating salary record."""
    salary: Optional[float] = Field(None, gt=0)
    bonus: Optional[float] = Field(None, ge=0)
    commission: Optional[float] = Field(None, ge=0)
    to_date: Optional[date] = None


class SalaryResponse(SalaryBase):
    """Salary response schema."""
    id: int
    uuid: UUID4
    emp_no: int
    from_date: date
    to_date: date
    total_compensation: float
    is_current: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================
# PAGINATION SCHEMAS
# ============================================

class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: str = Field("asc", regex="^(asc|desc)$", description="Sort order")


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(cls, items: list, total: int, page: int, page_size: int):
        """Create paginated response."""
        total_pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


# ============================================
# FILTER SCHEMAS
# ============================================

class EmployeeFilter(BaseModel):
    """Employee filter parameters."""
    search: Optional[str] = Field(None, description="Search in name, email")
    status: Optional[EmploymentStatusEnum] = None
    gender: Optional[GenderEnum] = None
    dept_no: Optional[str] = None
    hire_date_from: Optional[date] = None
    hire_date_to: Optional[date] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
