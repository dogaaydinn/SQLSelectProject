"""
Department Service Layer
Business logic for department operations
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.repositories.department_repository import DepartmentRepository
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.utils.cache import cache_manager
from app.core.logging import logger


class DepartmentService:
    """
    Service layer for department business logic.
    Orchestrates repository operations and enforces business rules.
    """

    def __init__(
        self,
        db: AsyncSession,
        department_repo: Optional[DepartmentRepository] = None,
    ):
        """
        Initialize service with database session and repository.

        Args:
            db: Database session
            department_repo: Department repository (optional)
        """
        self.db = db
        self.department_repo = department_repo or DepartmentRepository(db)

    async def create_department(
        self,
        department_data: DepartmentCreate,
    ) -> Dict[str, Any]:
        """
        Create new department.

        Args:
            department_data: Department creation data

        Returns:
            Created department

        Raises:
            ValueError: If business rules violated
        """
        # Business rule: Department name must be unique
        if await self.department_repo.dept_name_exists(department_data.dept_name):
            raise ValueError(f"Department name '{department_data.dept_name}' already exists")

        # Business rule: Department number must follow format (d\d{3})
        if not department_data.dept_no.startswith("d") or len(department_data.dept_no) != 4:
            raise ValueError("Department number must be in format 'd001', 'd002', etc.")

        try:
            dept_dict = department_data.model_dump(exclude_unset=True)
            department = await self.department_repo.create(dept_dict)

            await self.db.commit()

            # Invalidate caches
            await self._invalidate_department_caches()

            logger.info(
                f"Created department {department.dept_no}: {department.dept_name}"
            )

            return self._department_to_dict(department)

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to create department: {e}")
            raise ValueError("Failed to create department due to data constraint violation")

    async def get_department(
        self,
        dept_no: str,
        include_employees: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Get department by department number.

        Args:
            dept_no: Department number
            include_employees: Load employee relationships

        Returns:
            Department data or None
        """
        # Try cache first (only for simple queries)
        if not include_employees:
            cache_key = f"department:{dept_no}"
            cached_data = await cache_manager.get(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for department {dept_no}")
                return cached_data

        # Fetch from database
        department = await self.department_repo.get_by_dept_no(
            dept_no,
            include_employees=include_employees,
        )

        if not department:
            return None

        # Convert to dict
        dept_data = self._department_to_dict(department, include_employees)

        # Cache if not including relationships
        if not include_employees:
            await cache_manager.set(f"department:{dept_no}", dept_data, ttl=600)

        return dept_data

    async def update_department(
        self,
        dept_no: str,
        department_data: DepartmentUpdate,
    ) -> Optional[Dict[str, Any]]:
        """
        Update department information.

        Args:
            dept_no: Department number
            department_data: Update data

        Returns:
            Updated department or None

        Raises:
            ValueError: If business rules violated
        """
        # Check if department exists
        existing = await self.department_repo.get_by_dept_no(dept_no, include_employees=False)
        if not existing:
            return None

        # Business rule: Department name must be unique if being updated
        if department_data.dept_name:
            if await self.department_repo.dept_name_exists(
                department_data.dept_name,
                exclude_dept_no=dept_no,
            ):
                raise ValueError(f"Department name '{department_data.dept_name}' already exists")

        try:
            update_dict = department_data.model_dump(exclude_unset=True)
            updated_dept = await self.department_repo.update(
                dept_no,
                update_dict,
                id_field="dept_no",
            )

            await self.db.commit()

            # Invalidate cache
            await cache_manager.delete(f"department:{dept_no}")
            await self._invalidate_department_caches()

            logger.info(f"Updated department {dept_no}")

            return self._department_to_dict(updated_dept)

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to update department {dept_no}: {e}")
            raise ValueError("Failed to update department due to data constraint violation")

    async def delete_department(
        self,
        dept_no: str,
        soft_delete: bool = True,
    ) -> bool:
        """
        Delete department.

        Args:
            dept_no: Department number
            soft_delete: Use soft delete (default True)

        Returns:
            True if deleted, False if not found
        """
        # Business rule: Cannot delete department with active employees
        department = await self.department_repo.get_with_employees(dept_no, current_only=True)
        if department and hasattr(department, "current_employees") and department.current_employees:
            raise ValueError(
                f"Cannot delete department {dept_no}: has {len(department.current_employees)} active employees"
            )

        success = await self.department_repo.delete(
            dept_no,
            id_field="dept_no",
            soft_delete=soft_delete,
        )

        if success:
            await self.db.commit()

            # Invalidate cache
            await cache_manager.delete(f"department:{dept_no}")
            await self._invalidate_department_caches()

            logger.info(f"Deleted department {dept_no} (soft_delete={soft_delete})")

        return success

    async def search_departments(
        self,
        search_term: Optional[str] = None,
        is_active: Optional[bool] = None,
        min_budget: Optional[Decimal] = None,
        max_budget: Optional[Decimal] = None,
        location: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
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
        departments = await self.department_repo.search_departments(
            search_term=search_term,
            is_active=is_active,
            min_budget=min_budget,
            max_budget=max_budget,
            location=location,
            skip=skip,
            limit=limit,
        )

        return [self._department_to_dict(dept) for dept in departments]

    async def get_active_departments(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get all active departments.

        Args:
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of active departments
        """
        departments = await self.department_repo.get_active_departments(skip=skip, limit=limit)
        return [self._department_to_dict(dept) for dept in departments]

    async def get_department_statistics(
        self,
        dept_no: str,
    ) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a department.

        Args:
            dept_no: Department number

        Returns:
            Dictionary with statistics
        """
        # Try cache first
        cache_key = f"department:{dept_no}:statistics"
        cached_stats = await cache_manager.get(cache_key)
        if cached_stats:
            return cached_stats

        stats = await self.department_repo.get_department_statistics(dept_no)

        # Cache for 5 minutes
        await cache_manager.set(cache_key, stats, ttl=300)

        return stats

    async def update_department_budget(
        self,
        dept_no: str,
        new_budget: Decimal,
        reason: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update department budget with audit logging.

        Args:
            dept_no: Department number
            new_budget: New budget amount
            reason: Reason for budget change (optional)

        Returns:
            Updated department or None

        Raises:
            ValueError: If business rules violated
        """
        # Business rule: Budget must be positive
        if new_budget < 0:
            raise ValueError("Budget cannot be negative")

        # Get current department
        current = await self.department_repo.get_by_dept_no(dept_no, include_employees=False)
        if not current:
            return None

        # Log budget change in metadata
        metadata = current.metadata or {}
        budget_history = metadata.get("budget_history", [])
        budget_history.append({
            "old_budget": float(current.budget) if current.budget else 0.0,
            "new_budget": float(new_budget),
            "changed_at": logger.get_timestamp(),
            "reason": reason,
        })
        metadata["budget_history"] = budget_history

        # Update budget and metadata
        updated = await self.department_repo.update(
            dept_no,
            {
                "budget": new_budget,
                "metadata": metadata,
            },
            id_field="dept_no",
        )

        await self.db.commit()

        # Invalidate caches
        await cache_manager.delete(f"department:{dept_no}")
        await cache_manager.delete(f"department:{dept_no}:statistics")

        logger.info(
            f"Updated department {dept_no} budget from "
            f"{current.budget} to {new_budget}. Reason: {reason}"
        )

        return self._department_to_dict(updated)

    async def assign_department_manager(
        self,
        dept_no: str,
        manager_emp_no: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Assign manager to department.

        Args:
            dept_no: Department number
            manager_emp_no: Employee number of manager

        Returns:
            Updated department or None
        """
        updated = await self.department_repo.assign_manager(dept_no, manager_emp_no)

        if updated:
            await self.db.commit()

            # Invalidate caches
            await cache_manager.delete(f"department:{dept_no}")

            logger.info(f"Assigned manager {manager_emp_no} to department {dept_no}")

        return self._department_to_dict(updated) if updated else None

    async def get_departments_with_low_budget(
        self,
        threshold: Decimal,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get departments with budget below threshold.

        Args:
            threshold: Budget threshold
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of departments with low budget
        """
        departments = await self.department_repo.get_departments_with_low_budget(
            threshold=threshold,
            skip=skip,
            limit=limit,
        )

        return [self._department_to_dict(dept) for dept in departments]

    # ============================================
    # PRIVATE HELPER METHODS
    # ============================================

    def _department_to_dict(
        self,
        department: Any,
        include_employees: bool = False,
    ) -> Dict[str, Any]:
        """
        Convert department model to dictionary.

        Args:
            department: Department model instance
            include_employees: Include employee count

        Returns:
            Department dictionary
        """
        data = {
            "dept_no": department.dept_no,
            "dept_name": department.dept_name,
            "description": department.description,
            "manager_emp_no": department.manager_emp_no,
            "budget": float(department.budget) if department.budget else None,
            "location": department.location,
            "is_active": department.is_active,
            "metadata": department.metadata,
            "created_at": department.created_at.isoformat() if department.created_at else None,
            "updated_at": department.updated_at.isoformat() if department.updated_at else None,
        }

        if include_employees:
            # Add employee count if available
            if hasattr(department, "current_employees"):
                data["current_employee_count"] = len(department.current_employees)
            elif hasattr(department, "dept_emps"):
                data["total_employee_assignments"] = len(department.dept_emps)

        return data

    async def _invalidate_department_caches(self) -> None:
        """Invalidate department-related caches."""
        await cache_manager.delete_pattern("department:*")
        logger.debug("Invalidated department caches")
