"""
Cache Warming Service
Proactively warms cache with frequently accessed data on application startup
"""

import asyncio
from datetime import date
from typing import Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.logging import logger
from app.models.employee import Employee, EmploymentStatus
from app.models.department import Department
from app.models.salary import Salary
from app.models.dept_emp import DeptEmp
from app.utils.cache import cache_manager


class CacheWarmer:
    """
    Manages cache warming strategies for frequently accessed data.
    Implements intelligent pre-loading to reduce cold-start latency.
    """

    def __init__(self):
        self.warmed_keys: set = set()
        self.warming_stats: Dict[str, Any] = {}

    async def warm_all_caches(self) -> Dict[str, Any]:
        """
        Warm all critical caches on application startup.

        Returns:
            Dictionary with warming statistics
        """
        logger.info("Starting cache warming process...")
        start_time = asyncio.get_event_loop().time()

        stats = {
            "total_keys": 0,
            "total_time_ms": 0,
            "caches_warmed": [],
        }

        try:
            async with async_session_maker() as db:
                # Warm caches in priority order
                await self._warm_analytics_summary(db, stats)
                await self._warm_department_statistics(db, stats)
                await self._warm_salary_statistics(db, stats)
                await self._warm_employee_counts(db, stats)
                await self._warm_gender_diversity(db, stats)
                await self._warm_department_performance(db, stats)

            end_time = asyncio.get_event_loop().time()
            stats["total_time_ms"] = round((end_time - start_time) * 1000, 2)
            stats["total_keys"] = len(self.warmed_keys)

            logger.info(
                f"Cache warming completed: {stats['total_keys']} keys in "
                f"{stats['total_time_ms']}ms"
            )

        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            stats["error"] = str(e)

        self.warming_stats = stats
        return stats

    async def _warm_analytics_summary(
        self, db: AsyncSession, stats: Dict[str, Any]
    ) -> None:
        """Warm analytics summary cache (highest priority)."""
        try:
            # Total employees
            total_emp_query = select(func.count()).where(
                and_(
                    Employee.is_deleted == False,
                    Employee.status == EmploymentStatus.Active,
                )
            )
            total_emp_result = await db.execute(total_emp_query)
            total_employees = total_emp_result.scalar()

            # Total departments
            total_dept_query = select(func.count()).where(
                and_(Department.is_deleted == False, Department.is_active == True)
            )
            total_dept_result = await db.execute(total_dept_query)
            total_departments = total_dept_result.scalar()

            # Average salary
            avg_salary_query = select(func.avg(Salary.salary)).where(
                and_(Salary.to_date == date(9999, 12, 31), Salary.is_deleted == False)
            )
            avg_salary_result = await db.execute(avg_salary_query)
            avg_salary = avg_salary_result.scalar()

            # Total payroll
            total_payroll_query = select(func.sum(Salary.salary)).where(
                and_(Salary.to_date == date(9999, 12, 31), Salary.is_deleted == False)
            )
            total_payroll_result = await db.execute(total_payroll_query)
            total_payroll = total_payroll_result.scalar()

            # Average tenure
            avg_tenure_query = select(
                func.avg(
                    func.extract("days", func.current_date() - Employee.hire_date)
                )
            ).where(
                and_(
                    Employee.is_deleted == False,
                    Employee.status == EmploymentStatus.Active,
                )
            )
            avg_tenure_result = await db.execute(avg_tenure_query)
            avg_tenure_days = avg_tenure_result.scalar()

            summary_data = {
                "total_employees": total_employees or 0,
                "total_departments": total_departments or 0,
                "avg_salary": float(avg_salary) if avg_salary else None,
                "total_payroll": float(total_payroll) if total_payroll else None,
                "avg_tenure_days": (
                    float(avg_tenure_days) if avg_tenure_days else None
                ),
                "avg_tenure_years": (
                    round(float(avg_tenure_days) / 365, 2) if avg_tenure_days else None
                ),
            }

            # Cache with 10-minute TTL
            cache_key = "analytics_summary:"
            await cache_manager.set(cache_key, summary_data, ttl=600)
            self.warmed_keys.add(cache_key)

            stats["caches_warmed"].append("analytics_summary")
            logger.debug("Warmed: analytics_summary")

        except Exception as e:
            logger.warning(f"Failed to warm analytics_summary: {e}")

    async def _warm_department_statistics(
        self, db: AsyncSession, stats: Dict[str, Any]
    ) -> None:
        """Warm department statistics for all departments."""
        try:
            # Get all active departments
            dept_query = select(Department).where(
                and_(Department.is_deleted == False, Department.is_active == True)
            )
            dept_result = await db.execute(dept_query)
            departments = dept_result.scalars().all()

            for dept in departments:
                # Get employee count
                emp_count_query = select(func.count(DeptEmp.id)).where(
                    and_(
                        DeptEmp.dept_no == dept.dept_no,
                        DeptEmp.to_date == date(9999, 12, 31),
                        DeptEmp.is_deleted == False,
                    )
                )
                emp_count_result = await db.execute(emp_count_query)
                employee_count = emp_count_result.scalar() or 0

                # Get average salary
                avg_salary_query = (
                    select(func.avg(Salary.salary))
                    .join(DeptEmp, Salary.emp_no == DeptEmp.emp_no)
                    .where(
                        and_(
                            DeptEmp.dept_no == dept.dept_no,
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
                if dept.budget and avg_salary and employee_count > 0:
                    total_salaries = float(avg_salary) * employee_count
                    budget_utilization = (total_salaries / float(dept.budget)) * 100

                dept_stats = {
                    "dept_no": dept.dept_no,
                    "dept_name": dept.dept_name,
                    "employee_count": employee_count,
                    "avg_salary": avg_salary,
                    "budget": dept.budget,
                    "budget_utilization": budget_utilization,
                }

                # Cache with 10-minute TTL
                cache_key = f"department_stats:{dept.dept_no}"
                await cache_manager.set(cache_key, dept_stats, ttl=600)
                self.warmed_keys.add(cache_key)

            stats["caches_warmed"].append(
                f"department_stats ({len(departments)} depts)"
            )
            logger.debug(f"Warmed: department_stats for {len(departments)} departments")

        except Exception as e:
            logger.warning(f"Failed to warm department_statistics: {e}")

    async def _warm_salary_statistics(
        self, db: AsyncSession, stats: Dict[str, Any]
    ) -> None:
        """Warm overall salary statistics."""
        try:
            # Current salaries only
            query = select(Salary).where(
                and_(
                    Salary.to_date == date(9999, 12, 31), Salary.is_deleted == False
                )
            )

            # Get statistics
            stats_query = select(
                func.count(Salary.id).label("total_employees"),
                func.avg(Salary.salary).label("avg_salary"),
                func.min(Salary.salary).label("min_salary"),
                func.max(Salary.salary).label("max_salary"),
                func.sum(Salary.salary).label("total_payroll"),
                func.stddev(Salary.salary).label("std_deviation"),
            ).select_from(query.subquery())

            result = await db.execute(stats_query)
            salary_stats = result.one()

            # Calculate median (approximation)
            median_query = select(
                func.percentile_cont(0.5).within_group(Salary.salary.desc())
            ).select_from(query.subquery())

            try:
                median_result = await db.execute(median_query)
                median_salary = median_result.scalar()
            except:
                median_salary = None

            salary_data = {
                "total_employees": salary_stats.total_employees or 0,
                "avg_salary": salary_stats.avg_salary,
                "min_salary": salary_stats.min_salary,
                "max_salary": salary_stats.max_salary,
                "median_salary": median_salary,
                "total_payroll": salary_stats.total_payroll,
                "std_deviation": (
                    float(salary_stats.std_deviation)
                    if salary_stats.std_deviation
                    else None
                ),
            }

            # Cache with 10-minute TTL
            cache_key = "analytics_salary_stats:"
            await cache_manager.set(cache_key, salary_data, ttl=600)
            self.warmed_keys.add(cache_key)

            stats["caches_warmed"].append("salary_statistics")
            logger.debug("Warmed: salary_statistics")

        except Exception as e:
            logger.warning(f"Failed to warm salary_statistics: {e}")

    async def _warm_employee_counts(
        self, db: AsyncSession, stats: Dict[str, Any]
    ) -> None:
        """Warm employee count by status."""
        try:
            # Count by status
            status_query = (
                select(Employee.status, func.count(Employee.emp_no).label("count"))
                .where(Employee.is_deleted == False)
                .group_by(Employee.status)
            )

            result = await db.execute(status_query)
            rows = result.all()

            employee_counts = {str(row.status.value): row.count for row in rows}

            # Cache with 5-minute TTL
            cache_key = "employee_counts_by_status:"
            await cache_manager.set(cache_key, employee_counts, ttl=300)
            self.warmed_keys.add(cache_key)

            stats["caches_warmed"].append("employee_counts")
            logger.debug("Warmed: employee_counts")

        except Exception as e:
            logger.warning(f"Failed to warm employee_counts: {e}")

    async def _warm_gender_diversity(
        self, db: AsyncSession, stats: Dict[str, Any]
    ) -> None:
        """Warm gender diversity statistics."""
        try:
            # Active employees only
            query = select(Employee).where(
                and_(
                    Employee.is_deleted == False,
                    Employee.status == EmploymentStatus.Active,
                )
            )

            # Get total count
            total_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(total_query)
            total = total_result.scalar() or 1

            # Get gender distribution with salary
            gender_query = (
                select(
                    Employee.gender,
                    func.count(Employee.emp_no).label("count"),
                    func.avg(Salary.salary).label("avg_salary"),
                )
                .select_from(query.subquery().alias("emp"))
                .outerjoin(
                    Salary,
                    and_(
                        Salary.emp_no == Employee.emp_no,
                        Salary.to_date == date(9999, 12, 31),
                        Salary.is_deleted == False,
                    ),
                )
                .group_by(Employee.gender)
            )

            result = await db.execute(gender_query)
            rows = result.all()

            diversity_data = [
                {
                    "gender": str(row.gender.value if row.gender else "Unknown"),
                    "count": row.count,
                    "percentage": round((row.count / total) * 100, 2),
                    "avg_salary": row.avg_salary,
                }
                for row in rows
            ]

            # Cache with 10-minute TTL
            cache_key = "analytics_gender_div:"
            await cache_manager.set(cache_key, diversity_data, ttl=600)
            self.warmed_keys.add(cache_key)

            stats["caches_warmed"].append("gender_diversity")
            logger.debug("Warmed: gender_diversity")

        except Exception as e:
            logger.warning(f"Failed to warm gender_diversity: {e}")

    async def _warm_department_performance(
        self, db: AsyncSession, stats: Dict[str, Any]
    ) -> None:
        """Warm department performance metrics (optimized single query)."""
        try:
            # Single optimized query with all department metrics
            performance_query = (
                select(
                    Department.dept_no,
                    Department.dept_name,
                    Department.budget,
                    func.count(func.distinct(DeptEmp.emp_no)).label("employee_count"),
                    func.avg(Salary.salary).label("avg_salary"),
                    func.sum(Salary.salary).label("total_payroll"),
                    func.avg(
                        func.extract("days", func.current_date() - Employee.hire_date)
                    ).label("avg_tenure_days"),
                )
                .select_from(Department)
                .outerjoin(
                    DeptEmp,
                    and_(
                        Department.dept_no == DeptEmp.dept_no,
                        DeptEmp.to_date == date(9999, 12, 31),
                        DeptEmp.is_deleted == False,
                    ),
                )
                .outerjoin(
                    Salary,
                    and_(
                        DeptEmp.emp_no == Salary.emp_no,
                        Salary.to_date == date(9999, 12, 31),
                        Salary.is_deleted == False,
                    ),
                )
                .outerjoin(
                    Employee,
                    and_(
                        DeptEmp.emp_no == Employee.emp_no, Employee.is_deleted == False
                    ),
                )
                .where(Department.is_deleted == False)
                .group_by(Department.dept_no, Department.dept_name, Department.budget)
                .order_by(Department.dept_no)
            )

            result = await db.execute(performance_query)
            rows = result.all()

            performance_data = []
            for row in rows:
                budget_utilization = None
                if row.budget and row.total_payroll:
                    budget_utilization = (
                        float(row.total_payroll) / float(row.budget)
                    ) * 100

                performance_data.append(
                    {
                        "dept_no": row.dept_no,
                        "dept_name": row.dept_name,
                        "employee_count": row.employee_count or 0,
                        "avg_salary": row.avg_salary,
                        "total_payroll": row.total_payroll,
                        "budget": row.budget,
                        "budget_utilization": budget_utilization,
                        "avg_tenure_days": (
                            float(row.avg_tenure_days) if row.avg_tenure_days else None
                        ),
                    }
                )

            # Cache with 10-minute TTL
            cache_key = "analytics_dept_perf:"
            await cache_manager.set(cache_key, performance_data, ttl=600)
            self.warmed_keys.add(cache_key)

            stats["caches_warmed"].append("department_performance")
            logger.debug("Warmed: department_performance")

        except Exception as e:
            logger.warning(f"Failed to warm department_performance: {e}")

    async def schedule_refresh(self, interval_seconds: int = 300):
        """
        Schedule periodic cache refresh.

        Args:
            interval_seconds: Refresh interval (default: 5 minutes)
        """
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                logger.info("Running scheduled cache refresh...")
                await self.warm_all_caches()
            except Exception as e:
                logger.error(f"Scheduled cache refresh failed: {e}")


# Global cache warmer instance
cache_warmer = CacheWarmer()
