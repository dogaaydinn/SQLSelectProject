"""
Department API Endpoints
Complete CRUD operations for departments
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from decimal import Decimal

from app.core.database import get_db
from app.models.department import Department
from app.models.dept_emp import DeptEmp
from app.schemas.employee import PaginatedResponse
from app.utils.cache import cached, cache_manager
from pydantic import BaseModel, Field

router = APIRouter()


# Pydantic schemas for Department
class DepartmentBase(BaseModel):
    dept_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    manager_emp_no: Optional[int] = None
    budget: Optional[Decimal] = None
    location: Optional[str] = None
    is_active: bool = True


class DepartmentCreate(DepartmentBase):
    dept_no: str = Field(..., min_length=4, max_length=4, pattern=r"^d\d{3}$")


class DepartmentUpdate(BaseModel):
    dept_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    manager_emp_no: Optional[int] = None
    budget: Optional[Decimal] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentResponse(DepartmentBase):
    dept_no: str
    uuid: str
    created_at: str
    updated_at: str
    version: int
    is_deleted: bool

    class Config:
        from_attributes = True


class DepartmentStatistics(BaseModel):
    dept_no: str
    dept_name: str
    employee_count: int
    avg_salary: Optional[Decimal] = None
    budget: Optional[Decimal] = None
    budget_utilization: Optional[float] = None


@router.get("/", response_model=PaginatedResponse)
async def list_departments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    List departments with pagination and filtering.

    Args:
        page: Page number
        page_size: Items per page
        search: Search in department name
        is_active: Filter by active status
        db: Database session

    Returns:
        Paginated list of departments
    """
    query = select(Department).where(Department.is_deleted == False)

    # Apply filters
    if search:
        search_filter = or_(
            Department.dept_name.ilike(f"%{search}%"),
            Department.description.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    if is_active is not None:
        query = query.where(Department.is_active == is_active)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar()

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    departments = result.scalars().all()

    return PaginatedResponse.create(
        items=[DepartmentResponse.model_validate(dept) for dept in departments],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{dept_no}", response_model=DepartmentResponse)
@cached(key_prefix="department", ttl=300)
async def get_department(
    dept_no: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get department by ID.

    Args:
        dept_no: Department number
        db: Database session

    Returns:
        Department details
    """
    query = select(Department).where(
        and_(Department.dept_no == dept_no, Department.is_deleted == False)
    )
    result = await db.execute(query)
    department = result.scalar_one_or_none()

    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department {dept_no} not found",
        )

    return DepartmentResponse.model_validate(department)


@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    department_data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create new department.

    Args:
        department_data: Department data
        db: Database session

    Returns:
        Created department
    """
    # Check if department already exists
    query = select(Department).where(Department.dept_no == department_data.dept_no)
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Department {department_data.dept_no} already exists",
        )

    # Create department
    department = Department(**department_data.model_dump())

    db.add(department)
    await db.commit()
    await db.refresh(department)

    # Invalidate cache
    await cache_manager.delete_pattern("department:*")

    return DepartmentResponse.model_validate(department)


@router.put("/{dept_no}", response_model=DepartmentResponse)
async def update_department(
    dept_no: str,
    department_data: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update department.

    Args:
        dept_no: Department number
        department_data: Updated department data
        db: Database session

    Returns:
        Updated department
    """
    query = select(Department).where(
        and_(Department.dept_no == dept_no, Department.is_deleted == False)
    )
    result = await db.execute(query)
    department = result.scalar_one_or_none()

    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department {dept_no} not found",
        )

    # Update fields
    for field, value in department_data.model_dump(exclude_unset=True).items():
        setattr(department, field, value)

    await db.commit()
    await db.refresh(department)

    # Invalidate cache
    await cache_manager.delete(f"department:{dept_no}")
    await cache_manager.delete_pattern("department:*")

    return DepartmentResponse.model_validate(department)


@router.delete("/{dept_no}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    dept_no: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Soft delete department.

    Args:
        dept_no: Department number
        db: Database session
    """
    query = select(Department).where(
        and_(Department.dept_no == dept_no, Department.is_deleted == False)
    )
    result = await db.execute(query)
    department = result.scalar_one_or_none()

    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department {dept_no} not found",
        )

    # Soft delete
    department.is_deleted = True
    await db.commit()

    # Invalidate cache
    await cache_manager.delete(f"department:{dept_no}")
    await cache_manager.delete_pattern("department:*")

    return None


@router.get("/{dept_no}/employees")
async def get_department_employees(
    dept_no: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get employees in a department.

    Args:
        dept_no: Department number
        page: Page number
        page_size: Items per page
        current_only: Only show current employees
        db: Database session

    Returns:
        List of employees in department
    """
    # Check if department exists
    dept_query = select(Department).where(
        and_(Department.dept_no == dept_no, Department.is_deleted == False)
    )
    dept_result = await db.execute(dept_query)
    department = dept_result.scalar_one_or_none()

    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department {dept_no} not found",
        )

    # Build query for employees
    from app.models.employee import Employee

    query = (
        select(Employee)
        .join(DeptEmp, Employee.emp_no == DeptEmp.emp_no)
        .where(
            and_(
                DeptEmp.dept_no == dept_no,
                DeptEmp.is_deleted == False,
                Employee.is_deleted == False,
            )
        )
    )

    if current_only:
        from datetime import date
        query = query.where(DeptEmp.to_date == date(9999, 12, 31))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar()

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    employees = result.scalars().all()

    from app.schemas.employee import EmployeeResponse

    return PaginatedResponse.create(
        items=[EmployeeResponse.model_validate(emp) for emp in employees],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{dept_no}/statistics", response_model=DepartmentStatistics)
@cached(key_prefix="department_stats", ttl=600)
async def get_department_statistics(
    dept_no: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get department statistics.

    Args:
        dept_no: Department number
        db: Database session

    Returns:
        Department statistics
    """
    # Check if department exists
    dept_query = select(Department).where(
        and_(Department.dept_no == dept_no, Department.is_deleted == False)
    )
    dept_result = await db.execute(dept_query)
    department = dept_result.scalar_one_or_none()

    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department {dept_no} not found",
        )

    # Get employee count
    from datetime import date
    emp_count_query = select(func.count(DeptEmp.id)).where(
        and_(
            DeptEmp.dept_no == dept_no,
            DeptEmp.to_date == date(9999, 12, 31),
            DeptEmp.is_deleted == False,
        )
    )
    emp_count_result = await db.execute(emp_count_query)
    employee_count = emp_count_result.scalar() or 0

    # Get average salary
    from app.models.salary import Salary

    avg_salary_query = (
        select(func.avg(Salary.salary))
        .join(DeptEmp, Salary.emp_no == DeptEmp.emp_no)
        .where(
            and_(
                DeptEmp.dept_no == dept_no,
                DeptEmp.to_date == date(9999, 12, 31),
                Salary.to_date == date(9999, 12, 31),
                DeptEmp.is_deleted == False,
                Salary.is_deleted == False,
            )
        )
    )
    avg_salary_result = await db.execute(avg_salary_query)
    avg_salary = avg_salary_result.scalar()

    # Calculate budget utilization
    budget_utilization = None
    if department.budget and avg_salary and employee_count > 0:
        total_salaries = float(avg_salary) * employee_count
        budget_utilization = (total_salaries / float(department.budget)) * 100

    return DepartmentStatistics(
        dept_no=department.dept_no,
        dept_name=department.dept_name,
        employee_count=employee_count,
        avg_salary=avg_salary,
        budget=department.budget,
        budget_utilization=budget_utilization,
    )
