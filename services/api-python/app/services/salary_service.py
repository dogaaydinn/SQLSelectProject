"""
Salary Service Layer
Business logic for salary operations
"""

from typing import List, Optional, Dict, Any
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.repositories.salary_repository import SalaryRepository
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.salary import SalaryCreate, SalaryUpdate
from app.utils.cache import cache_manager
from app.core.logging import logger


class SalaryService:
    """
    Service layer for salary business logic.
    Orchestrates repository operations and enforces business rules.
    """

    def __init__(
        self,
        db: AsyncSession,
        salary_repo: Optional[SalaryRepository] = None,
        employee_repo: Optional[EmployeeRepository] = None,
    ):
        """
        Initialize service with database session and repositories.

        Args:
            db: Database session
            salary_repo: Salary repository (optional)
            employee_repo: Employee repository (optional)
        """
        self.db = db
        self.salary_repo = salary_repo or SalaryRepository(db)
        self.employee_repo = employee_repo or EmployeeRepository(db)

    async def create_salary(
        self,
        salary_data: SalaryCreate,
    ) -> Dict[str, Any]:
        """
        Create new salary record.

        Args:
            salary_data: Salary creation data

        Returns:
            Created salary

        Raises:
            ValueError: If business rules violated
        """
        # Business rule: Employee must exist
        employee_exists = await self.employee_repo.exists(
            salary_data.emp_no,
            id_field="emp_no",
        )
        if not employee_exists:
            raise ValueError(f"Employee {salary_data.emp_no} does not exist")

        # Business rule: Cannot have duplicate salary records for same start date
        if await self.salary_repo.salary_exists_for_period(
            salary_data.emp_no,
            salary_data.from_date,
        ):
            raise ValueError(
                f"Salary record already exists for employee {salary_data.emp_no} "
                f"starting on {salary_data.from_date}"
            )

        # Business rule: from_date cannot be in the future
        if salary_data.from_date > date.today():
            raise ValueError("Salary start date cannot be in the future")

        # Business rule: to_date must be after from_date
        if salary_data.to_date and salary_data.to_date < salary_data.from_date:
            raise ValueError("Salary end date must be after start date")

        try:
            salary_dict = salary_data.model_dump(exclude_unset=True)
            salary = await self.salary_repo.create(salary_dict)

            await self.db.commit()

            # Invalidate caches
            await self._invalidate_salary_caches(salary_data.emp_no)

            logger.info(
                f"Created salary for employee {salary.emp_no}: "
                f"${salary.salary} starting {salary.from_date}"
            )

            return self._salary_to_dict(salary)

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to create salary: {e}")
            raise ValueError("Failed to create salary due to data constraint violation")

    async def update_salary(
        self,
        salary_id: int,
        salary_data: SalaryUpdate,
    ) -> Optional[Dict[str, Any]]:
        """
        Update salary record.

        Args:
            salary_id: Salary ID
            salary_data: Update data

        Returns:
            Updated salary or None

        Raises:
            ValueError: If business rules violated
        """
        # Get existing salary
        existing = await self.salary_repo.get_by_id(salary_id)
        if not existing:
            return None

        # Business rule: Cannot update historical salaries
        if existing.to_date != date(9999, 12, 31):
            raise ValueError("Cannot update historical salary records")

        try:
            update_dict = salary_data.model_dump(exclude_unset=True)
            updated_salary = await self.salary_repo.update(
                salary_id,
                update_dict,
                id_field="id",
            )

            await self.db.commit()

            # Invalidate caches
            await self._invalidate_salary_caches(existing.emp_no)

            logger.info(f"Updated salary {salary_id}")

            return self._salary_to_dict(updated_salary)

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to update salary {salary_id}: {e}")
            raise ValueError("Failed to update salary due to data constraint violation")

    async def get_employee_salaries(
        self,
        emp_no: int,
        include_employee: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get all salary records for an employee.

        Args:
            emp_no: Employee number
            include_employee: Include employee data

        Returns:
            List of salary records
        """
        # Try cache first (only for simple queries)
        if not include_employee:
            cache_key = f"salary:employee:{emp_no}"
            cached_data = await cache_manager.get(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for employee {emp_no} salaries")
                return cached_data

        salaries = await self.salary_repo.get_by_employee(
            emp_no,
            include_employee=include_employee,
        )

        salary_data = [self._salary_to_dict(s, include_employee) for s in salaries]

        # Cache if not including relationships
        if not include_employee:
            await cache_manager.set(cache_key, salary_data, ttl=600)

        return salary_data

    async def get_current_salary(
        self,
        emp_no: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Get current salary for an employee.

        Args:
            emp_no: Employee number

        Returns:
            Current salary or None
        """
        # Try cache first
        cache_key = f"salary:current:{emp_no}"
        cached_data = await cache_manager.get(cache_key)
        if cached_data:
            return cached_data

        salary = await self.salary_repo.get_current_salary(emp_no)
        if not salary:
            return None

        salary_data = self._salary_to_dict(salary)

        # Cache for 10 minutes
        await cache_manager.set(cache_key, salary_data, ttl=600)

        return salary_data

    async def get_salary_history(
        self,
        emp_no: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get salary history for an employee.

        Args:
            emp_no: Employee number
            start_date: Start of date range (optional)
            end_date: End of date range (optional)

        Returns:
            List of salary records
        """
        salaries = await self.salary_repo.get_salary_history(
            emp_no,
            start_date=start_date,
            end_date=end_date,
        )

        return [self._salary_to_dict(s) for s in salaries]

    async def get_salary_statistics(
        self,
        current_only: bool = True,
    ) -> Dict[str, Any]:
        """
        Get comprehensive salary statistics.

        Args:
            current_only: Only include current salaries

        Returns:
            Salary statistics
        """
        # Try cache first
        cache_key = f"salary:statistics:current={current_only}"
        cached_stats = await cache_manager.get(cache_key)
        if cached_stats:
            return cached_stats

        stats = await self.salary_repo.get_salary_statistics(current_only=current_only)

        # Cache for 5 minutes
        await cache_manager.set(cache_key, stats, ttl=300)

        return stats

    async def get_department_salary_statistics(
        self,
        current_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get average salary by department.

        Args:
            current_only: Only include current salaries

        Returns:
            List of department salary statistics
        """
        # Try cache first
        cache_key = f"salary:department_stats:current={current_only}"
        cached_stats = await cache_manager.get(cache_key)
        if cached_stats:
            return cached_stats

        stats = await self.salary_repo.calculate_average_salary_by_department(
            current_only=current_only
        )

        # Cache for 5 minutes
        await cache_manager.set(cache_key, stats, ttl=300)

        return stats

    async def get_top_earners(
        self,
        limit: int = 100,
        department: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get top earners.

        Args:
            limit: Maximum number of results
            department: Filter by department (optional)

        Returns:
            List of top earners
        """
        salaries = await self.salary_repo.get_top_earners(
            limit=limit,
            department=department,
            include_employee=True,
        )

        return [self._salary_to_dict(s, include_employee=True) for s in salaries]

    async def adjust_salary(
        self,
        emp_no: int,
        new_salary: Decimal,
        from_date: date,
        reason: Optional[str] = None,
        bonus: Optional[Decimal] = None,
        commission: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """
        Adjust employee salary with business logic.

        Args:
            emp_no: Employee number
            new_salary: New salary amount
            from_date: Effective date
            reason: Reason for adjustment (optional)
            bonus: Bonus amount (optional)
            commission: Commission amount (optional)

        Returns:
            New salary record

        Raises:
            ValueError: If business rules violated
        """
        # Business rule: New salary must be positive
        if new_salary <= 0:
            raise ValueError("Salary must be positive")

        # Get current salary
        current = await self.salary_repo.get_current_salary(emp_no)
        if not current:
            raise ValueError(f"No current salary found for employee {emp_no}")

        # Business rule: Cannot adjust salary to a past date
        if from_date < date.today():
            raise ValueError("Salary adjustment date cannot be in the past")

        # Business rule: Log significant salary changes (>20% increase or any decrease)
        change_percent = ((new_salary - current.salary) / current.salary) * 100
        if abs(change_percent) > 20:
            logger.warning(
                f"Large salary change for employee {emp_no}: "
                f"{change_percent:.2f}% ({current.salary} -> {new_salary}). "
                f"Reason: {reason}"
            )

        try:
            # Close current salary record
            await self.salary_repo.update(
                current.id,
                {"to_date": from_date},
                id_field="id",
            )

            # Create new salary record
            new_salary_data = {
                "emp_no": emp_no,
                "salary": new_salary,
                "from_date": from_date,
                "to_date": date(9999, 12, 31),
                "currency": current.currency,
                "salary_type": current.salary_type,
                "bonus": bonus or Decimal(0),
                "commission": commission or Decimal(0),
                "metadata": {
                    "adjustment_reason": reason,
                    "previous_salary": float(current.salary),
                    "change_percent": float(change_percent),
                },
            }

            new_salary_record = await self.salary_repo.create(new_salary_data)
            await self.db.commit()

            # Invalidate caches
            await self._invalidate_salary_caches(emp_no)

            logger.info(
                f"Adjusted salary for employee {emp_no} from ${current.salary} to "
                f"${new_salary} ({change_percent:+.2f}%)"
            )

            return self._salary_to_dict(new_salary_record)

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to adjust salary for employee {emp_no}: {e}")
            raise ValueError("Failed to adjust salary due to data constraint violation")

    async def get_salary_growth_rate(
        self,
        emp_no: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate salary growth rate for an employee.

        Args:
            emp_no: Employee number

        Returns:
            Growth rate statistics or None
        """
        # Try cache first
        cache_key = f"salary:growth:{emp_no}"
        cached_data = await cache_manager.get(cache_key)
        if cached_data:
            return cached_data

        growth = await self.salary_repo.get_salary_growth_rate(emp_no)

        if growth:
            # Cache for 1 hour
            await cache_manager.set(cache_key, growth, ttl=3600)

        return growth

    async def get_salary_changes_in_range(
        self,
        start_date: date,
        end_date: date,
        min_change_percent: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get salary changes within date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            min_change_percent: Minimum percentage change to include

        Returns:
            List of salary changes
        """
        return await self.salary_repo.get_salary_changes_in_range(
            start_date=start_date,
            end_date=end_date,
            min_change_percent=min_change_percent,
        )

    async def get_recent_salary_changes(
        self,
        days: int = 30,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get recent salary changes.

        Args:
            days: Number of days to look back
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of recent salary changes
        """
        salaries = await self.salary_repo.get_recent_salary_changes(
            days=days,
            skip=skip,
            limit=limit,
        )

        return [self._salary_to_dict(s, include_employee=True) for s in salaries]

    # ============================================
    # PRIVATE HELPER METHODS
    # ============================================

    def _salary_to_dict(
        self,
        salary: Any,
        include_employee: bool = False,
    ) -> Dict[str, Any]:
        """
        Convert salary model to dictionary.

        Args:
            salary: Salary model instance
            include_employee: Include employee data

        Returns:
            Salary dictionary
        """
        data = {
            "id": salary.id,
            "emp_no": salary.emp_no,
            "salary": float(salary.salary),
            "currency": salary.currency,
            "from_date": salary.from_date.isoformat(),
            "to_date": salary.to_date.isoformat(),
            "salary_type": salary.salary_type,
            "bonus": float(salary.bonus) if salary.bonus else 0.0,
            "commission": float(salary.commission) if salary.commission else 0.0,
            "total_compensation": float(salary.total_compensation),
            "is_current": salary.is_current,
            "metadata": salary.metadata,
            "created_at": salary.created_at.isoformat() if salary.created_at else None,
            "updated_at": salary.updated_at.isoformat() if salary.updated_at else None,
        }

        if include_employee and hasattr(salary, "employee") and salary.employee:
            data["employee"] = {
                "emp_no": salary.employee.emp_no,
                "first_name": salary.employee.first_name,
                "last_name": salary.employee.last_name,
                "email": salary.employee.email,
                "status": salary.employee.status.value if hasattr(salary.employee.status, "value") else salary.employee.status,
            }

        return data

    async def _invalidate_salary_caches(self, emp_no: int) -> None:
        """Invalidate salary-related caches for an employee."""
        await cache_manager.delete(f"salary:employee:{emp_no}")
        await cache_manager.delete(f"salary:current:{emp_no}")
        await cache_manager.delete(f"salary:growth:{emp_no}")
        await cache_manager.delete_pattern("salary:statistics:*")
        await cache_manager.delete_pattern("salary:department_stats:*")
        logger.debug(f"Invalidated salary caches for employee {emp_no}")
