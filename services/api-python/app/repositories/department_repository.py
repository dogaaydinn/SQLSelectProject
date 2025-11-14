"""
Department Repository
Domain-specific data access for Department entity
"""

from typing import Optional, List, Dict, Any
from decimal import Decimal
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.repositories.base import BaseRepository


class DepartmentRepository(BaseRepository[Department]):
    """Repository for Department entity with domain-specific queries."""

    def __init__(self, db: AsyncSession):
        super().__init__(Department, db)

    async def get_by_dept_no(
        self,
        dept_no: str,
        include_employees: bool = True,
    ) -> Optional[Department]:
        """
        Get department by department number with relationships.

        Args:
            dept_no: Department number (e.g., "d001")
            include_employees: Load department-employee relationships

        Returns:
            Department instance or None
        """
        relationships = []
        if include_employees:
            relationships = ["dept_emps"]

        return await self.get_by_id(
            dept_no,
            id_field="dept_no",
            relationships=relationships,
        )

    async def get_by_dept_name(self, dept_name: str) -> Optional[Department]:
        """
        Get department by name.

        Args:
            dept_name: Department name

        Returns:
            Department instance or None
        """
        query = select(Department).where(
            and_(
                Department.dept_name == dept_name,
                Department.is_deleted == False,
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def search_departments(
        self,
        search_term: Optional[str] = None,
        is_active: Optional[bool] = None,
        min_budget: Optional[Decimal] = None,
        max_budget: Optional[Decimal] = None,
        location: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Department]:
        """
        Search departments with multiple criteria.

        Args:
            search_term: Search in name or description
            is_active: Filter by active status
            min_budget: Minimum budget filter
            max_budget: Maximum budget filter
            location: Location filter
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of matching departments
        """
        query = select(Department).where(Department.is_deleted == False)

        # Search in name or description
        if search_term:
            search_filter = or_(
                Department.dept_name.ilike(f"%{search_term}%"),
                Department.description.ilike(f"%{search_term}%"),
            )
            query = query.where(search_filter)

        # Active status filter
        if is_active is not None:
            query = query.where(Department.is_active == is_active)

        # Budget range filters
        if min_budget is not None:
            query = query.where(Department.budget >= min_budget)
        if max_budget is not None:
            query = query.where(Department.budget <= max_budget)

        # Location filter
        if location:
            query = query.where(Department.location.ilike(f"%{location}%"))

        # Pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_active_departments(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Department]:
        """
        Get all active departments.

        Args:
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of active departments
        """
        query = (
            select(Department)
            .where(
                and_(
                    Department.is_active == True,
                    Department.is_deleted == False,
                )
            )
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_with_employees(
        self,
        dept_no: str,
        current_only: bool = True,
    ) -> Optional[Department]:
        """
        Get department with all employee relationships eagerly loaded.

        Args:
            dept_no: Department number
            current_only: Only include current employees (to_date = 9999-12-31)

        Returns:
            Department with employees loaded
        """
        from app.models.dept_emp import DeptEmp
        from datetime import date

        query = (
            select(Department)
            .options(
                selectinload(Department.dept_emps).selectinload(DeptEmp.employee)
            )
            .where(
                and_(
                    Department.dept_no == dept_no,
                    Department.is_deleted == False,
                )
            )
        )

        result = await self.db.execute(query)
        department = result.scalar_one_or_none()

        if department and current_only:
            # Filter for current employees in Python (already loaded)
            department.current_employees = [
                de.employee
                for de in department.dept_emps
                if de.to_date == date(9999, 12, 31) and not de.is_deleted
            ]

        return department

    async def get_department_statistics(
        self,
        dept_no: str,
    ) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a department.

        Args:
            dept_no: Department number

        Returns:
            Dictionary with statistics (employee_count, avg_salary, total_budget, etc.)
        """
        from app.models.dept_emp import DeptEmp
        from app.models.salary import Salary
        from datetime import date

        # Get employee count
        employee_count_query = (
            select(func.count(DeptEmp.emp_no))
            .where(
                and_(
                    DeptEmp.dept_no == dept_no,
                    DeptEmp.to_date == date(9999, 12, 31),
                    DeptEmp.is_deleted == False,
                )
            )
        )
        employee_count_result = await self.db.execute(employee_count_query)
        employee_count = employee_count_result.scalar()

        # Get average salary for department
        avg_salary_query = (
            select(func.avg(Salary.salary))
            .select_from(DeptEmp)
            .join(Salary, DeptEmp.emp_no == Salary.emp_no)
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
        avg_salary_result = await self.db.execute(avg_salary_query)
        avg_salary = avg_salary_result.scalar()

        # Get department info
        department = await self.get_by_dept_no(dept_no, include_employees=False)

        return {
            "dept_no": dept_no,
            "dept_name": department.dept_name if department else None,
            "employee_count": employee_count or 0,
            "avg_salary": float(avg_salary) if avg_salary else 0.0,
            "budget": float(department.budget) if department and department.budget else 0.0,
            "location": department.location if department else None,
            "is_active": department.is_active if department else False,
        }

    async def count_by_active_status(self) -> Dict[str, int]:
        """
        Count departments grouped by active status.

        Returns:
            Dictionary of active status: count
        """
        query = (
            select(Department.is_active, func.count(Department.dept_no))
            .where(Department.is_deleted == False)
            .group_by(Department.is_active)
        )

        result = await self.db.execute(query)
        return {("active" if is_active else "inactive"): count for is_active, count in result.all()}

    async def get_departments_by_budget_range(
        self,
        min_budget: Decimal,
        max_budget: Decimal,
    ) -> List[Department]:
        """
        Get departments within a budget range.

        Args:
            min_budget: Minimum budget
            max_budget: Maximum budget

        Returns:
            List of departments
        """
        query = select(Department).where(
            and_(
                Department.budget >= min_budget,
                Department.budget <= max_budget,
                Department.is_deleted == False,
            )
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def dept_name_exists(
        self,
        dept_name: str,
        exclude_dept_no: Optional[str] = None,
    ) -> bool:
        """
        Check if department name is already in use.

        Args:
            dept_name: Department name to check
            exclude_dept_no: Exclude this department number (for updates)

        Returns:
            True if name exists, False otherwise
        """
        query = select(func.count()).select_from(Department).where(
            and_(
                Department.dept_name == dept_name,
                Department.is_deleted == False,
            )
        )

        if exclude_dept_no:
            query = query.where(Department.dept_no != exclude_dept_no)

        result = await self.db.execute(query)
        return result.scalar() > 0

    async def get_departments_with_low_budget(
        self,
        threshold: Decimal,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Department]:
        """
        Get departments with budget below threshold.

        Args:
            threshold: Budget threshold
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of departments with low budget
        """
        query = (
            select(Department)
            .where(
                and_(
                    Department.budget < threshold,
                    Department.is_deleted == False,
                )
            )
            .order_by(Department.budget.asc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_budget(
        self,
        dept_no: str,
        new_budget: Decimal,
    ) -> Optional[Department]:
        """
        Update department budget.

        Args:
            dept_no: Department number
            new_budget: New budget amount

        Returns:
            Updated department or None
        """
        return await self.update(
            dept_no,
            {"budget": new_budget},
            id_field="dept_no",
        )

    async def assign_manager(
        self,
        dept_no: str,
        manager_emp_no: int,
    ) -> Optional[Department]:
        """
        Assign manager to department.

        Args:
            dept_no: Department number
            manager_emp_no: Employee number of manager

        Returns:
            Updated department or None
        """
        return await self.update(
            dept_no,
            {"manager_emp_no": manager_emp_no},
            id_field="dept_no",
        )
