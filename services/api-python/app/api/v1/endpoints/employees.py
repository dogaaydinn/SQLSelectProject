"""
Employee API Endpoints
Complete CRUD operations for employees
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.core.database import get_db
from app.models.employee import Employee
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    EmployeeFilter,
    PaginationParams,
    PaginatedResponse,
)
from app.utils.cache import cached, cache_manager

router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    List employees with pagination and filtering.

    Args:
        page: Page number
        page_size: Items per page
        search: Search in name, email
        status: Filter by employment status
        db: Database session

    Returns:
        Paginated list of employees
    """
    query = select(Employee).where(Employee.is_deleted == False)

    # Apply filters
    if search:
        search_filter = or_(
            Employee.first_name.ilike(f"%{search}%"),
            Employee.last_name.ilike(f"%{search}%"),
            Employee.email.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    if status:
        query = query.where(Employee.status == status)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar()

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    employees = result.scalars().all()

    return PaginatedResponse.create(
        items=[EmployeeResponse.model_validate(emp) for emp in employees],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{emp_no}", response_model=EmployeeResponse)
@cached(key_prefix="employee", ttl=300)
async def get_employee(
    emp_no: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get employee by ID.

    Args:
        emp_no: Employee number
        db: Database session

    Returns:
        Employee details
    """
    query = select(Employee).where(
        and_(Employee.emp_no == emp_no, Employee.is_deleted == False)
    )
    result = await db.execute(query)
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {emp_no} not found",
        )

    return EmployeeResponse.model_validate(employee)


@router.post("/", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    employee_data: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create new employee.

    Args:
        employee_data: Employee data
        db: Database session

    Returns:
        Created employee
    """
    # Create employee
    employee = Employee(**employee_data.model_dump())

    db.add(employee)
    await db.commit()
    await db.refresh(employee)

    # Invalidate cache
    await cache_manager.delete_pattern("employee:*")

    return EmployeeResponse.model_validate(employee)


@router.put("/{emp_no}", response_model=EmployeeResponse)
async def update_employee(
    emp_no: int,
    employee_data: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update employee.

    Args:
        emp_no: Employee number
        employee_data: Updated employee data
        db: Database session

    Returns:
        Updated employee
    """
    query = select(Employee).where(
        and_(Employee.emp_no == emp_no, Employee.is_deleted == False)
    )
    result = await db.execute(query)
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {emp_no} not found",
        )

    # Update fields
    for field, value in employee_data.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)

    await db.commit()
    await db.refresh(employee)

    # Invalidate cache
    await cache_manager.delete(f"employee:{emp_no}")
    await cache_manager.delete_pattern("employee:*")

    return EmployeeResponse.model_validate(employee)


@router.delete("/{emp_no}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    emp_no: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Soft delete employee.

    Args:
        emp_no: Employee number
        db: Database session
    """
    query = select(Employee).where(
        and_(Employee.emp_no == emp_no, Employee.is_deleted == False)
    )
    result = await db.execute(query)
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {emp_no} not found",
        )

    # Soft delete
    employee.is_deleted = True
    await db.commit()

    # Invalidate cache
    await cache_manager.delete(f"employee:{emp_no}")
    await cache_manager.delete_pattern("employee:*")

    return None
