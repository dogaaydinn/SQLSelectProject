"""
Salary API Endpoints
Complete CRUD operations for salaries
"""

from datetime import date
from typing import List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.salary import Salary
from app.models.employee import Employee
from app.schemas.employee import PaginatedResponse
from app.utils.cache import cached, cache_manager

router = APIRouter()


# Pydantic schemas for Salary
class SalaryBase(BaseModel):
    salary: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    from_date: date
    to_date: date = date(9999, 12, 31)
    salary_type: str = Field(default="Base", max_length=50)
    bonus: Optional[Decimal] = Field(default=Decimal(0), ge=0, decimal_places=2)
    commission: Optional[Decimal] = Field(default=Decimal(0), ge=0, decimal_places=2)


class SalaryCreate(SalaryBase):
    emp_no: int


class SalaryUpdate(BaseModel):
    salary: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    salary_type: Optional[str] = Field(None, max_length=50)
    bonus: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    commission: Optional[Decimal] = Field(None, ge=0, decimal_places=2)


class SalaryResponse(SalaryBase):
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
    employee_name: str
    employee_email: Optional[str] = None


@router.get("/", response_model=PaginatedResponse)
async def list_salaries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    emp_no: Optional[int] = Query(None),
    min_salary: Optional[Decimal] = Query(None),
    max_salary: Optional[Decimal] = Query(None),
    current_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    List salaries with pagination and filtering.

    Args:
        page: Page number
        page_size: Items per page
        emp_no: Filter by employee number
        min_salary: Minimum salary
        max_salary: Maximum salary
        current_only: Only show current salaries
        db: Database session

    Returns:
        Paginated list of salaries
    """
    query = select(Salary).where(Salary.is_deleted == False)

    # Apply filters
    if emp_no:
        query = query.where(Salary.emp_no == emp_no)

    if min_salary:
        query = query.where(Salary.salary >= min_salary)

    if max_salary:
        query = query.where(Salary.salary <= max_salary)

    if current_only:
        query = query.where(Salary.to_date == date(9999, 12, 31))

    # Order by from_date descending
    query = query.order_by(desc(Salary.from_date))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar()

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    salaries = result.scalars().all()

    return PaginatedResponse.create(
        items=[SalaryResponse.model_validate(sal) for sal in salaries],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{salary_id}", response_model=SalaryResponse)
@cached(key_prefix="salary", ttl=300)
async def get_salary(
    salary_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get salary by ID.

    Args:
        salary_id: Salary ID
        db: Database session

    Returns:
        Salary details
    """
    query = select(Salary).where(
        and_(Salary.id == salary_id, Salary.is_deleted == False)
    )
    result = await db.execute(query)
    salary = result.scalar_one_or_none()

    if not salary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Salary {salary_id} not found",
        )

    return SalaryResponse.model_validate(salary)


@router.post("/", response_model=SalaryResponse, status_code=status.HTTP_201_CREATED)
async def create_salary(
    salary_data: SalaryCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create new salary record.

    Args:
        salary_data: Salary data
        db: Database session

    Returns:
        Created salary
    """
    # Validate employee exists
    emp_query = select(Employee).where(
        and_(Employee.emp_no == salary_data.emp_no, Employee.is_deleted == False)
    )
    emp_result = await db.execute(emp_query)
    employee = emp_result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {salary_data.emp_no} not found",
        )

    # Validate dates
    if salary_data.to_date < salary_data.from_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="to_date must be greater than or equal to from_date",
        )

    # Check for overlapping salary records
    overlap_query = select(Salary).where(
        and_(
            Salary.emp_no == salary_data.emp_no,
            Salary.is_deleted == False,
            or_(
                and_(
                    Salary.from_date <= salary_data.from_date,
                    Salary.to_date >= salary_data.from_date,
                ),
                and_(
                    Salary.from_date <= salary_data.to_date,
                    Salary.to_date >= salary_data.to_date,
                ),
            ),
        )
    )
    overlap_result = await db.execute(overlap_query)
    overlapping = overlap_result.scalar_one_or_none()

    if overlapping:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Salary record overlaps with existing record (from {overlapping.from_date} to {overlapping.to_date})",
        )

    # Create salary
    salary = Salary(**salary_data.model_dump())

    db.add(salary)
    await db.commit()
    await db.refresh(salary)

    # Invalidate cache
    await cache_manager.delete_pattern("salary:*")
    await cache_manager.delete_pattern(f"employee:{salary_data.emp_no}:*")

    return SalaryResponse.model_validate(salary)


@router.put("/{salary_id}", response_model=SalaryResponse)
async def update_salary(
    salary_id: int,
    salary_data: SalaryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update salary.

    Args:
        salary_id: Salary ID
        salary_data: Updated salary data
        db: Database session

    Returns:
        Updated salary
    """
    query = select(Salary).where(
        and_(Salary.id == salary_id, Salary.is_deleted == False)
    )
    result = await db.execute(query)
    salary = result.scalar_one_or_none()

    if not salary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Salary {salary_id} not found",
        )

    # Update fields
    update_data = salary_data.model_dump(exclude_unset=True)

    # Validate dates if both are being updated
    from_date = update_data.get("from_date", salary.from_date)
    to_date = update_data.get("to_date", salary.to_date)

    if to_date < from_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="to_date must be greater than or equal to from_date",
        )

    for field, value in update_data.items():
        setattr(salary, field, value)

    await db.commit()
    await db.refresh(salary)

    # Invalidate cache
    await cache_manager.delete(f"salary:{salary_id}")
    await cache_manager.delete_pattern("salary:*")
    await cache_manager.delete_pattern(f"employee:{salary.emp_no}:*")

    return SalaryResponse.model_validate(salary)


@router.delete("/{salary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_salary(
    salary_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Soft delete salary.

    Args:
        salary_id: Salary ID
        db: Database session
    """
    query = select(Salary).where(
        and_(Salary.id == salary_id, Salary.is_deleted == False)
    )
    result = await db.execute(query)
    salary = result.scalar_one_or_none()

    if not salary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Salary {salary_id} not found",
        )

    # Soft delete
    salary.is_deleted = True
    await db.commit()

    # Invalidate cache
    await cache_manager.delete(f"salary:{salary_id}")
    await cache_manager.delete_pattern("salary:*")
    await cache_manager.delete_pattern(f"employee:{salary.emp_no}:*")

    return None


# Employee-specific salary endpoints
@router.get("/employee/{emp_no}", response_model=PaginatedResponse)
@cached(key_prefix="employee_salaries", ttl=300)
async def get_employee_salaries(
    emp_no: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get salary history for an employee.

    Args:
        emp_no: Employee number
        page: Page number
        page_size: Items per page
        db: Database session

    Returns:
        Employee salary history
    """
    # Validate employee exists
    emp_query = select(Employee).where(
        and_(Employee.emp_no == emp_no, Employee.is_deleted == False)
    )
    emp_result = await db.execute(emp_query)
    employee = emp_result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {emp_no} not found",
        )

    # Get salary history
    query = (
        select(Salary)
        .where(and_(Salary.emp_no == emp_no, Salary.is_deleted == False))
        .order_by(desc(Salary.from_date))
    )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar()

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    salaries = result.scalars().all()

    return PaginatedResponse.create(
        items=[SalaryResponse.model_validate(sal) for sal in salaries],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/employee/{emp_no}/current", response_model=SalaryResponse)
@cached(key_prefix="employee_current_salary", ttl=600)
async def get_employee_current_salary(
    emp_no: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get current salary for an employee.

    Args:
        emp_no: Employee number
        db: Database session

    Returns:
        Current salary
    """
    # Validate employee exists
    emp_query = select(Employee).where(
        and_(Employee.emp_no == emp_no, Employee.is_deleted == False)
    )
    emp_result = await db.execute(emp_query)
    employee = emp_result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {emp_no} not found",
        )

    # Get current salary
    query = select(Salary).where(
        and_(
            Salary.emp_no == emp_no,
            Salary.to_date == date(9999, 12, 31),
            Salary.is_deleted == False,
        )
    )
    result = await db.execute(query)
    salary = result.scalar_one_or_none()

    if not salary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No current salary found for employee {emp_no}",
        )

    return SalaryResponse.model_validate(salary)
