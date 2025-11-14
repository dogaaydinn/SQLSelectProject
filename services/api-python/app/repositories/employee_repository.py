"""
Employee Repository
Domain-specific data access for Employee entity
"""

from typing import Optional, List
from datetime import date
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee, EmploymentStatus, Gender
from app.repositories.base import BaseRepository


class EmployeeRepository(BaseRepository[Employee]):
    """Repository for Employee entity with domain-specific queries."""

    def __init__(self, db: AsyncSession):
        super().__init__(Employee, db)

    async def get_by_employee_number(
        self,
        emp_no: int,
        include_relationships: bool = True,
    ) -> Optional[Employee]:
        """
        Get employee by employee number with all relationships.

        Args:
            emp_no: Employee number
            include_relationships: Load salaries, departments, titles

        Returns:
            Employee instance or None
        """
        relationships = []
        if include_relationships:
            relationships = ["salaries", "departments", "titles"]

        return await self.get_by_id(
            emp_no,
            id_field="emp_no",
            relationships=relationships,
        )

    async def search_employees(
        self,
        search_term: Optional[str] = None,
        status: Optional[EmploymentStatus] = None,
        gender: Optional[Gender] = None,
        department: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Employee]:
        """
        Search employees with multiple criteria.

        Args:
            search_term: Search in name or email
            status: Employment status filter
            gender: Gender filter
            department: Department number filter
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of matching employees
        """
        query = select(Employee).where(Employee.is_deleted == False)

        # Search in name or email
        if search_term:
            search_filter = or_(
                Employee.first_name.ilike(f"%{search_term}%"),
                Employee.last_name.ilike(f"%{search_term}%"),
                Employee.email.ilike(f"%{search_term}%"),
            )
            query = query.where(search_filter)

        # Status filter
        if status:
            query = query.where(Employee.status == status)

        # Gender filter
        if gender:
            query = query.where(Employee.gender == gender)

        # Department filter (requires join)
        if department:
            from app.models.dept_emp import DeptEmp

            query = (
                query.join(DeptEmp, Employee.emp_no == DeptEmp.emp_no)
                .where(
                    and_(
                        DeptEmp.dept_no == department,
                        DeptEmp.to_date == date(9999, 12, 31),  # Current assignment
                        DeptEmp.is_deleted == False,
                    )
                )
            )

        # Pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_email(self, email: str) -> Optional[Employee]:
        """
        Get employee by email address.

        Args:
            email: Email address

        Returns:
            Employee instance or None
        """
        query = select(Employee).where(
            and_(
                Employee.email == email,
                Employee.is_deleted == False,
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_active_employees(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Employee]:
        """
        Get all active (non-terminated) employees.

        Args:
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of active employees
        """
        query = (
            select(Employee)
            .where(
                and_(
                    Employee.status == EmploymentStatus.ACTIVE,
                    Employee.is_deleted == False,
                )
            )
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_employees_by_hire_date_range(
        self,
        start_date: date,
        end_date: date,
    ) -> List[Employee]:
        """
        Get employees hired within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of employees
        """
        query = select(Employee).where(
            and_(
                Employee.hire_date >= start_date,
                Employee.hire_date <= end_date,
                Employee.is_deleted == False,
            )
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_status(self) -> dict:
        """
        Count employees grouped by employment status.

        Returns:
            Dictionary of status: count
        """
        query = (
            select(Employee.status, func.count(Employee.emp_no))
            .where(Employee.is_deleted == False)
            .group_by(Employee.status)
        )

        result = await self.db.execute(query)
        return {status: count for status, count in result.all()}

    async def count_by_gender(self) -> dict:
        """
        Count employees grouped by gender.

        Returns:
            Dictionary of gender: count
        """
        query = (
            select(Employee.gender, func.count(Employee.emp_no))
            .where(Employee.is_deleted == False)
            .group_by(Employee.gender)
        )

        result = await self.db.execute(query)
        return {gender.value: count for gender, count in result.all()}

    async def get_with_current_salary(
        self,
        emp_no: int,
    ) -> Optional[Employee]:
        """
        Get employee with their current salary eagerly loaded.

        Args:
            emp_no: Employee number

        Returns:
            Employee with current salary
        """
        from app.models.salary import Salary

        query = (
            select(Employee)
            .options(selectinload(Employee.salaries))
            .where(
                and_(
                    Employee.emp_no == emp_no,
                    Employee.is_deleted == False,
                )
            )
        )

        result = await self.db.execute(query)
        employee = result.scalar_one_or_none()

        if employee and employee.salaries:
            # Filter for current salary in Python (already loaded)
            employee.current_salary = next(
                (
                    s
                    for s in employee.salaries
                    if s.to_date == date(9999, 12, 31) and not s.is_deleted
                ),
                None,
            )

        return employee

    async def email_exists(self, email: str, exclude_emp_no: Optional[int] = None) -> bool:
        """
        Check if email is already in use.

        Args:
            email: Email to check
            exclude_emp_no: Exclude this employee number (for updates)

        Returns:
            True if email exists, False otherwise
        """
        query = select(func.count()).select_from(Employee).where(
            and_(
                Employee.email == email,
                Employee.is_deleted == False,
            )
        )

        if exclude_emp_no:
            query = query.where(Employee.emp_no != exclude_emp_no)

        result = await self.db.execute(query)
        return result.scalar() > 0
