"""
Salary Repository
Domain-specific data access for Salary entity
"""

from typing import Optional, List, Dict, Any
from datetime import date
from decimal import Decimal
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.salary import Salary
from app.repositories.base import BaseRepository


class SalaryRepository(BaseRepository[Salary]):
    """Repository for Salary entity with domain-specific queries."""

    def __init__(self, db: AsyncSession):
        super().__init__(Salary, db)

    async def get_by_employee(
        self,
        emp_no: int,
        include_employee: bool = False,
    ) -> List[Salary]:
        """
        Get all salary records for an employee.

        Args:
            emp_no: Employee number
            include_employee: Load employee relationship

        Returns:
            List of salary records ordered by from_date descending
        """
        query = (
            select(Salary)
            .where(
                and_(
                    Salary.emp_no == emp_no,
                    Salary.is_deleted == False,
                )
            )
            .order_by(desc(Salary.from_date))
        )

        if include_employee:
            query = query.options(selectinload(Salary.employee))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_current_salary(
        self,
        emp_no: int,
        include_employee: bool = False,
    ) -> Optional[Salary]:
        """
        Get current salary for an employee.

        Args:
            emp_no: Employee number
            include_employee: Load employee relationship

        Returns:
            Current salary record or None
        """
        query = select(Salary).where(
            and_(
                Salary.emp_no == emp_no,
                Salary.to_date == date(9999, 12, 31),
                Salary.is_deleted == False,
            )
        )

        if include_employee:
            query = query.options(selectinload(Salary.employee))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_salary_history(
        self,
        emp_no: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Salary]:
        """
        Get salary history for an employee within a date range.

        Args:
            emp_no: Employee number
            start_date: Start of date range (optional)
            end_date: End of date range (optional)

        Returns:
            List of salary records in chronological order
        """
        query = select(Salary).where(
            and_(
                Salary.emp_no == emp_no,
                Salary.is_deleted == False,
            )
        )

        if start_date:
            query = query.where(Salary.from_date >= start_date)
        if end_date:
            query = query.where(Salary.from_date <= end_date)

        query = query.order_by(Salary.from_date.asc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_salary_changes_in_range(
        self,
        start_date: date,
        end_date: date,
        min_change_percent: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get salary changes within a date range with percentage change.

        Args:
            start_date: Start of date range
            end_date: End of date range
            min_change_percent: Minimum percentage change to include

        Returns:
            List of salary change records with change percentage
        """
        from app.models.employee import Employee

        query = (
            select(
                Salary.emp_no,
                Employee.first_name,
                Employee.last_name,
                Salary.from_date,
                Salary.salary,
                func.lag(Salary.salary).over(
                    partition_by=Salary.emp_no,
                    order_by=Salary.from_date
                ).label("previous_salary"),
            )
            .select_from(Salary)
            .join(Employee, Salary.emp_no == Employee.emp_no)
            .where(
                and_(
                    Salary.from_date >= start_date,
                    Salary.from_date <= end_date,
                    Salary.is_deleted == False,
                    Employee.is_deleted == False,
                )
            )
            .order_by(Salary.from_date.desc())
        )

        result = await self.db.execute(query)
        rows = result.all()

        changes = []
        for row in rows:
            if row.previous_salary:
                change_percent = (
                    (float(row.salary) - float(row.previous_salary))
                    / float(row.previous_salary)
                    * 100
                )

                if min_change_percent is None or abs(change_percent) >= min_change_percent:
                    changes.append({
                        "emp_no": row.emp_no,
                        "first_name": row.first_name,
                        "last_name": row.last_name,
                        "change_date": row.from_date,
                        "new_salary": float(row.salary),
                        "previous_salary": float(row.previous_salary),
                        "change_amount": float(row.salary) - float(row.previous_salary),
                        "change_percent": round(change_percent, 2),
                    })

        return changes

    async def calculate_average_salary_by_department(
        self,
        current_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Calculate average salary by department.

        Args:
            current_only: Only include current salaries

        Returns:
            List of department salary statistics
        """
        from app.models.dept_emp import DeptEmp
        from app.models.department import Department

        query = (
            select(
                Department.dept_no,
                Department.dept_name,
                func.avg(Salary.salary).label("avg_salary"),
                func.min(Salary.salary).label("min_salary"),
                func.max(Salary.salary).label("max_salary"),
                func.count(Salary.id).label("employee_count"),
            )
            .select_from(Salary)
            .join(DeptEmp, Salary.emp_no == DeptEmp.emp_no)
            .join(Department, DeptEmp.dept_no == Department.dept_no)
            .where(
                and_(
                    Salary.is_deleted == False,
                    DeptEmp.is_deleted == False,
                    Department.is_deleted == False,
                )
            )
        )

        if current_only:
            query = query.where(
                and_(
                    Salary.to_date == date(9999, 12, 31),
                    DeptEmp.to_date == date(9999, 12, 31),
                )
            )

        query = query.group_by(Department.dept_no, Department.dept_name)
        query = query.order_by(desc("avg_salary"))

        result = await self.db.execute(query)

        return [
            {
                "dept_no": row.dept_no,
                "dept_name": row.dept_name,
                "avg_salary": float(row.avg_salary) if row.avg_salary else 0.0,
                "min_salary": float(row.min_salary) if row.min_salary else 0.0,
                "max_salary": float(row.max_salary) if row.max_salary else 0.0,
                "employee_count": row.employee_count,
            }
            for row in result.all()
        ]

    async def get_salary_statistics(
        self,
        current_only: bool = True,
    ) -> Dict[str, Any]:
        """
        Get comprehensive salary statistics across all employees.

        Args:
            current_only: Only include current salaries

        Returns:
            Dictionary with salary statistics
        """
        query = select(
            func.avg(Salary.salary).label("avg_salary"),
            func.min(Salary.salary).label("min_salary"),
            func.max(Salary.salary).label("max_salary"),
            func.percentile_cont(0.5).within_group(Salary.salary).label("median_salary"),
            func.count(Salary.id).label("total_count"),
        ).where(Salary.is_deleted == False)

        if current_only:
            query = query.where(Salary.to_date == date(9999, 12, 31))

        result = await self.db.execute(query)
        row = result.one()

        return {
            "avg_salary": float(row.avg_salary) if row.avg_salary else 0.0,
            "min_salary": float(row.min_salary) if row.min_salary else 0.0,
            "max_salary": float(row.max_salary) if row.max_salary else 0.0,
            "median_salary": float(row.median_salary) if row.median_salary else 0.0,
            "total_count": row.total_count,
        }

    async def get_top_earners(
        self,
        limit: int = 100,
        department: Optional[str] = None,
        include_employee: bool = True,
    ) -> List[Salary]:
        """
        Get top earners by current salary.

        Args:
            limit: Maximum number of results
            department: Filter by department (optional)
            include_employee: Load employee relationship

        Returns:
            List of top salary records
        """
        query = (
            select(Salary)
            .where(
                and_(
                    Salary.to_date == date(9999, 12, 31),
                    Salary.is_deleted == False,
                )
            )
            .order_by(desc(Salary.salary))
            .limit(limit)
        )

        if department:
            from app.models.dept_emp import DeptEmp

            query = (
                query
                .join(DeptEmp, Salary.emp_no == DeptEmp.emp_no)
                .where(
                    and_(
                        DeptEmp.dept_no == department,
                        DeptEmp.to_date == date(9999, 12, 31),
                        DeptEmp.is_deleted == False,
                    )
                )
            )

        if include_employee:
            query = query.options(selectinload(Salary.employee))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_salaries_by_range(
        self,
        min_salary: Decimal,
        max_salary: Decimal,
        current_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Salary]:
        """
        Get salaries within a salary range.

        Args:
            min_salary: Minimum salary
            max_salary: Maximum salary
            current_only: Only include current salaries
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of salary records
        """
        query = select(Salary).where(
            and_(
                Salary.salary >= min_salary,
                Salary.salary <= max_salary,
                Salary.is_deleted == False,
            )
        )

        if current_only:
            query = query.where(Salary.to_date == date(9999, 12, 31))

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def salary_exists_for_period(
        self,
        emp_no: int,
        from_date: date,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """
        Check if salary already exists for employee starting on a date.

        Args:
            emp_no: Employee number
            from_date: Start date to check
            exclude_id: Exclude this salary ID (for updates)

        Returns:
            True if salary exists, False otherwise
        """
        query = select(func.count()).select_from(Salary).where(
            and_(
                Salary.emp_no == emp_no,
                Salary.from_date == from_date,
                Salary.is_deleted == False,
            )
        )

        if exclude_id:
            query = query.where(Salary.id != exclude_id)

        result = await self.db.execute(query)
        return result.scalar() > 0

    async def get_salary_growth_rate(
        self,
        emp_no: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate salary growth rate for an employee.

        Args:
            emp_no: Employee number

        Returns:
            Dictionary with growth statistics or None
        """
        salaries = await self.get_salary_history(emp_no)

        if len(salaries) < 2:
            return None

        first_salary = salaries[0]
        latest_salary = salaries[-1]

        total_growth = float(latest_salary.salary) - float(first_salary.salary)
        growth_percent = (total_growth / float(first_salary.salary)) * 100

        # Calculate years between first and latest
        years = (latest_salary.from_date - first_salary.from_date).days / 365.25
        annual_growth_rate = growth_percent / years if years > 0 else 0

        return {
            "emp_no": emp_no,
            "first_salary": float(first_salary.salary),
            "first_salary_date": first_salary.from_date,
            "latest_salary": float(latest_salary.salary),
            "latest_salary_date": latest_salary.from_date,
            "total_growth": total_growth,
            "growth_percent": round(growth_percent, 2),
            "years": round(years, 2),
            "annual_growth_rate": round(annual_growth_rate, 2),
            "number_of_raises": len(salaries) - 1,
        }

    async def get_recent_salary_changes(
        self,
        days: int = 30,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Salary]:
        """
        Get recent salary changes within last N days.

        Args:
            days: Number of days to look back
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of recent salary records
        """
        from datetime import timedelta

        cutoff_date = date.today() - timedelta(days=days)

        query = (
            select(Salary)
            .options(selectinload(Salary.employee))
            .where(
                and_(
                    Salary.from_date >= cutoff_date,
                    Salary.is_deleted == False,
                )
            )
            .order_by(desc(Salary.from_date))
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_salary_range(
        self,
        ranges: List[tuple[Decimal, Decimal]],
        current_only: bool = True,
    ) -> Dict[str, int]:
        """
        Count salaries in predefined ranges.

        Args:
            ranges: List of (min, max) tuples defining salary ranges
            current_only: Only include current salaries

        Returns:
            Dictionary of range: count
        """
        results = {}

        for min_sal, max_sal in ranges:
            query = select(func.count()).select_from(Salary).where(
                and_(
                    Salary.salary >= min_sal,
                    Salary.salary < max_sal,
                    Salary.is_deleted == False,
                )
            )

            if current_only:
                query = query.where(Salary.to_date == date(9999, 12, 31))

            result = await self.db.execute(query)
            count = result.scalar()
            results[f"${min_sal}-${max_sal}"] = count

        return results
