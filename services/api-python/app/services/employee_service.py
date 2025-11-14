"""
Employee Service Layer
Business logic for employee operations
"""

from typing import List, Optional, Dict, Any
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.repositories.employee_repository import EmployeeRepository
from app.repositories.salary_repository import SalaryRepository
from app.models.employee import EmploymentStatus, Gender
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.utils.cache import cache_manager
from app.core.logging import logger


class EmployeeService:
    """
    Service layer for employee business logic.
    Orchestrates repository operations and enforces business rules.
    """

    def __init__(
        self,
        db: AsyncSession,
        employee_repo: Optional[EmployeeRepository] = None,
        salary_repo: Optional[SalaryRepository] = None,
    ):
        """
        Initialize service with database session and repositories.

        Args:
            db: Database session
            employee_repo: Employee repository (optional, will be created if not provided)
            salary_repo: Salary repository (optional, will be created if not provided)
        """
        self.db = db
        self.employee_repo = employee_repo or EmployeeRepository(db)
        self.salary_repo = salary_repo or SalaryRepository(db)

    async def create_employee(
        self,
        employee_data: EmployeeCreate,
        initial_salary: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """
        Create new employee with optional initial salary.

        Args:
            employee_data: Employee creation data
            initial_salary: Optional initial salary

        Returns:
            Created employee with ID

        Raises:
            ValueError: If business rules violated
            IntegrityError: If database constraints violated
        """
        # Business rule: Email must be unique if provided
        if employee_data.email:
            if await self.employee_repo.email_exists(employee_data.email):
                raise ValueError(f"Email {employee_data.email} already exists")

        # Business rule: Employee must be at least 16 years old at hire date
        age_at_hire = (employee_data.hire_date - employee_data.birth_date).days / 365.25
        if age_at_hire < 16:
            raise ValueError("Employee must be at least 16 years old at hire date")

        try:
            # Create employee
            employee_dict = employee_data.model_dump(exclude_unset=True)
            employee = await self.employee_repo.create(employee_dict)

            # Create initial salary if provided
            if initial_salary:
                await self._create_initial_salary(employee.emp_no, initial_salary, employee_data.hire_date)

            await self.db.commit()

            # Invalidate relevant caches
            await self._invalidate_employee_caches()

            logger.info(
                f"Created employee {employee.emp_no}: {employee.first_name} {employee.last_name}"
            )

            return {
                "emp_no": employee.emp_no,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "email": employee.email,
                "status": employee.status,
            }

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to create employee: {e}")
            raise ValueError("Failed to create employee due to data constraint violation")

    async def get_employee(
        self,
        emp_no: int,
        include_relationships: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Get employee by employee number.

        Args:
            emp_no: Employee number
            include_relationships: Load related data (salaries, departments, titles)

        Returns:
            Employee data or None
        """
        # Try cache first
        cache_key = f"employee:{emp_no}"
        cached_data = await cache_manager.get(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for employee {emp_no}")
            return cached_data

        # Fetch from database
        employee = await self.employee_repo.get_by_employee_number(
            emp_no,
            include_relationships=include_relationships,
        )

        if not employee:
            return None

        # Convert to dict and cache
        employee_data = self._employee_to_dict(employee, include_relationships)
        await cache_manager.set(cache_key, employee_data, ttl=300)

        return employee_data

    async def update_employee(
        self,
        emp_no: int,
        employee_data: EmployeeUpdate,
    ) -> Optional[Dict[str, Any]]:
        """
        Update employee information.

        Args:
            emp_no: Employee number
            employee_data: Update data

        Returns:
            Updated employee data or None

        Raises:
            ValueError: If business rules violated
        """
        # Check if employee exists
        existing = await self.employee_repo.get_by_employee_number(emp_no, include_relationships=False)
        if not existing:
            return None

        # Business rule: Email must be unique if being updated
        if employee_data.email:
            if await self.employee_repo.email_exists(employee_data.email, exclude_emp_no=emp_no):
                raise ValueError(f"Email {employee_data.email} already exists")

        try:
            # Update employee
            update_dict = employee_data.model_dump(exclude_unset=True)
            updated_employee = await self.employee_repo.update(
                emp_no,
                update_dict,
                id_field="emp_no",
            )

            await self.db.commit()

            # Invalidate cache
            await cache_manager.delete(f"employee:{emp_no}")
            await self._invalidate_employee_caches()

            logger.info(f"Updated employee {emp_no}")

            return self._employee_to_dict(updated_employee, include_relationships=False)

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to update employee {emp_no}: {e}")
            raise ValueError("Failed to update employee due to data constraint violation")

    async def delete_employee(
        self,
        emp_no: int,
        soft_delete: bool = True,
    ) -> bool:
        """
        Delete employee (soft or hard delete).

        Args:
            emp_no: Employee number
            soft_delete: Use soft delete (default True)

        Returns:
            True if deleted, False if not found
        """
        success = await self.employee_repo.delete(emp_no, id_field="emp_no", soft_delete=soft_delete)

        if success:
            await self.db.commit()

            # Invalidate cache
            await cache_manager.delete(f"employee:{emp_no}")
            await self._invalidate_employee_caches()

            logger.info(f"Deleted employee {emp_no} (soft_delete={soft_delete})")

        return success

    async def search_employees(
        self,
        search_term: Optional[str] = None,
        status: Optional[EmploymentStatus] = None,
        gender: Optional[Gender] = None,
        department: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
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
        employees = await self.employee_repo.search_employees(
            search_term=search_term,
            status=status,
            gender=gender,
            department=department,
            skip=skip,
            limit=limit,
        )

        return [self._employee_to_dict(emp, include_relationships=False) for emp in employees]

    async def get_active_employees(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get all active employees.

        Args:
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of active employees
        """
        employees = await self.employee_repo.get_active_employees(skip=skip, limit=limit)
        return [self._employee_to_dict(emp, include_relationships=False) for emp in employees]

    async def get_employee_statistics(self) -> Dict[str, Any]:
        """
        Get employee statistics.

        Returns:
            Dictionary with employee statistics
        """
        # Try cache first
        cache_key = "employee:statistics"
        cached_stats = await cache_manager.get(cache_key)
        if cached_stats:
            return cached_stats

        # Calculate statistics
        status_counts = await self.employee_repo.count_by_status()
        gender_counts = await self.employee_repo.count_by_gender()
        total_count = await self.employee_repo.count()

        stats = {
            "total_employees": total_count,
            "by_status": status_counts,
            "by_gender": gender_counts,
        }

        # Cache for 5 minutes
        await cache_manager.set(cache_key, stats, ttl=300)

        return stats

    async def update_employee_status(
        self,
        emp_no: int,
        new_status: EmploymentStatus,
        termination_date: Optional[date] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update employee status with business logic.

        Args:
            emp_no: Employee number
            new_status: New employment status
            termination_date: Termination date (required if status is TERMINATED)

        Returns:
            Updated employee or None

        Raises:
            ValueError: If business rules violated
        """
        # Business rule: Termination date required when terminating
        if new_status == EmploymentStatus.TERMINATED and not termination_date:
            raise ValueError("Termination date required when terminating employee")

        # Business rule: Cannot terminate to a past date before hire date
        employee = await self.employee_repo.get_by_employee_number(emp_no, include_relationships=False)
        if not employee:
            return None

        if termination_date and termination_date < employee.hire_date:
            raise ValueError("Termination date cannot be before hire date")

        # Update status
        update_data = {"status": new_status}
        if termination_date:
            update_data["metadata"] = {
                **employee.metadata,
                "termination_date": termination_date.isoformat(),
            }

        updated = await self.employee_repo.update(emp_no, update_data, id_field="emp_no")
        await self.db.commit()

        # Invalidate caches
        await cache_manager.delete(f"employee:{emp_no}")
        await self._invalidate_employee_caches()

        logger.info(f"Updated employee {emp_no} status to {new_status}")

        return self._employee_to_dict(updated, include_relationships=False)

    async def get_employee_with_current_salary(
        self,
        emp_no: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Get employee with current salary information.

        Args:
            emp_no: Employee number

        Returns:
            Employee data with current salary
        """
        employee = await self.employee_repo.get_with_current_salary(emp_no)
        if not employee:
            return None

        employee_dict = self._employee_to_dict(employee, include_relationships=False)

        # Add current salary if available
        if hasattr(employee, "current_salary") and employee.current_salary:
            employee_dict["current_salary"] = {
                "salary": float(employee.current_salary.salary),
                "from_date": employee.current_salary.from_date.isoformat(),
                "currency": employee.current_salary.currency,
            }

        return employee_dict

    # ============================================
    # PRIVATE HELPER METHODS
    # ============================================

    async def _create_initial_salary(
        self,
        emp_no: int,
        salary_amount: Decimal,
        from_date: date,
    ) -> None:
        """
        Create initial salary record for new employee.

        Args:
            emp_no: Employee number
            salary_amount: Initial salary amount
            from_date: Salary start date
        """
        salary_data = {
            "emp_no": emp_no,
            "salary": salary_amount,
            "from_date": from_date,
            "to_date": date(9999, 12, 31),
            "currency": "USD",
            "salary_type": "Base",
        }

        await self.salary_repo.create(salary_data)
        logger.info(f"Created initial salary for employee {emp_no}: ${salary_amount}")

    def _employee_to_dict(
        self,
        employee: Any,
        include_relationships: bool = False,
    ) -> Dict[str, Any]:
        """
        Convert employee model to dictionary.

        Args:
            employee: Employee model instance
            include_relationships: Include related data

        Returns:
            Employee dictionary
        """
        data = {
            "emp_no": employee.emp_no,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "middle_name": employee.middle_name,
            "birth_date": employee.birth_date.isoformat(),
            "gender": employee.gender.value if hasattr(employee.gender, "value") else employee.gender,
            "hire_date": employee.hire_date.isoformat(),
            "status": employee.status.value if hasattr(employee.status, "value") else employee.status,
            "email": employee.email,
            "phone": employee.phone,
            "address_line1": employee.address_line1,
            "address_line2": employee.address_line2,
            "city": employee.city,
            "state": employee.state,
            "country": employee.country,
            "postal_code": employee.postal_code,
            "created_at": employee.created_at.isoformat() if employee.created_at else None,
            "updated_at": employee.updated_at.isoformat() if employee.updated_at else None,
        }

        if include_relationships:
            # Add relationship counts
            data["salary_count"] = len(employee.salaries) if employee.salaries else 0
            data["department_count"] = len(employee.departments) if employee.departments else 0
            data["title_count"] = len(employee.titles) if employee.titles else 0

        return data

    async def _invalidate_employee_caches(self) -> None:
        """Invalidate employee-related caches."""
        await cache_manager.delete_pattern("employee:statistics")
        await cache_manager.delete_pattern("employee:list:*")
        logger.debug("Invalidated employee caches")
