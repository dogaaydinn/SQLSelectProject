"""
Analytics API Endpoints
Provides statistical analysis and aggregations
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, case

from app.core.database import get_db
from app.models.employee import Employee, EmploymentStatus
from app.models.department import Department
from app.models.salary import Salary
from app.models.dept_emp import DeptEmp
from app.schemas.analytics import (
    SalaryStatistics,
    SalaryDistribution,
    DepartmentPerformance,
    EmployeeTrends,
    GenderDiversity,
    TitleDistribution,
    AnalyticsSummary,
)
from app.utils.cache import cached, cache_manager

router = APIRouter()


@router.get("/salary-statistics", response_model=SalaryStatistics)
@cached(key_prefix="analytics_salary_stats", ttl=600)
async def get_salary_statistics(
    dept_no: Optional[str] = Query(None),
    current_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive salary statistics.

    Args:
        dept_no: Filter by department
        current_only: Only include current salaries
        db: Database session

    Returns:
        Salary statistics
    """
    # Build base query
    query = select(Salary).where(Salary.is_deleted == False)

    if current_only:
        query = query.where(Salary.to_date == date(9999, 12, 31))

    if dept_no:
        query = (
            query.join(DeptEmp, Salary.emp_no == DeptEmp.emp_no)
            .where(and_(DeptEmp.dept_no == dept_no, DeptEmp.is_deleted == False))
        )
        if current_only:
            query = query.where(DeptEmp.to_date == date(9999, 12, 31))

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
    stats = result.one()

    # Calculate median (approximation using percentile_cont)
    median_query = select(
        func.percentile_cont(0.5).within_group(Salary.salary.desc())
    ).select_from(query.subquery())

    try:
        median_result = await db.execute(median_query)
        median_salary = median_result.scalar()
    except:
        median_salary = None

    return SalaryStatistics(
        total_employees=stats.total_employees or 0,
        avg_salary=stats.avg_salary,
        min_salary=stats.min_salary,
        max_salary=stats.max_salary,
        median_salary=median_salary,
        total_payroll=stats.total_payroll,
        std_deviation=float(stats.std_deviation) if stats.std_deviation else None,
    )


@router.get("/salary-distribution", response_model=List[SalaryDistribution])
@cached(key_prefix="analytics_salary_dist", ttl=600)
async def get_salary_distribution(
    current_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get salary distribution by ranges.

    Args:
        current_only: Only include current salaries
        db: Database session

    Returns:
        Salary distribution
    """
    # Build query
    query = select(Salary).where(Salary.is_deleted == False)

    if current_only:
        query = query.where(Salary.to_date == date(9999, 12, 31))

    # Get total count
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 1  # Avoid division by zero

    # Define salary ranges and count
    salary_ranges = [
        ("< $40,000", 0, 40000),
        ("$40,000 - $60,000", 40000, 60000),
        ("$60,000 - $80,000", 60000, 80000),
        ("$80,000 - $100,000", 80000, 100000),
        ("$100,000 - $150,000", 100000, 150000),
        ("> $150,000", 150000, float("inf")),
    ]

    distribution = []
    for range_label, min_val, max_val in salary_ranges:
        range_query = query.where(Salary.salary >= min_val)
        if max_val != float("inf"):
            range_query = range_query.where(Salary.salary < max_val)

        count_query = select(func.count()).select_from(range_query.subquery())
        count_result = await db.execute(count_query)
        count = count_result.scalar() or 0

        distribution.append(
            SalaryDistribution(
                salary_range=range_label,
                count=count,
                percentage=round((count / total) * 100, 2),
            )
        )

    return distribution


@router.get("/department-performance", response_model=List[DepartmentPerformance])
@cached(key_prefix="analytics_dept_perf", ttl=600)
async def get_department_performance(
    db: AsyncSession = Depends(get_db),
):
    """
    Get performance metrics for all departments.
    OPTIMIZED: Single query with joins and GROUP BY to prevent N+1 queries.

    Args:
        db: Database session

    Returns:
        Department performance metrics
    """
    # Single optimized query with all department metrics
    # Uses CTEs and window functions for efficient aggregation
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
                DeptEmp.emp_no == Employee.emp_no,
                Employee.is_deleted == False,
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
        # Calculate budget utilization
        budget_utilization = None
        if row.budget and row.total_payroll:
            budget_utilization = (float(row.total_payroll) / float(row.budget)) * 100

        performance_data.append(
            DepartmentPerformance(
                dept_no=row.dept_no,
                dept_name=row.dept_name,
                employee_count=row.employee_count or 0,
                avg_salary=row.avg_salary,
                total_payroll=row.total_payroll,
                budget=row.budget,
                budget_utilization=budget_utilization,
                avg_tenure_days=float(row.avg_tenure_days) if row.avg_tenure_days else None,
            )
        )

    return performance_data


@router.get("/employee-trends", response_model=List[EmployeeTrends])
@cached(key_prefix="analytics_emp_trends", ttl=600)
async def get_employee_trends(
    months: int = Query(12, ge=1, le=60),
    db: AsyncSession = Depends(get_db),
):
    """
    Get employee hiring and termination trends.

    Args:
        months: Number of months to analyze
        db: Database session

    Returns:
        Employee trends
    """
    # This is a simplified version - in production, you'd want to
    # calculate this month by month
    from dateutil.relativedelta import relativedelta

    trends = []
    now = datetime.now().date()

    for i in range(months, 0, -1):
        period_start = now - relativedelta(months=i)
        period_end = now - relativedelta(months=i - 1)
        period_label = period_start.strftime("%Y-%m")

        # Get new hires
        hires_query = select(func.count()).where(
            and_(
                Employee.hire_date >= period_start,
                Employee.hire_date < period_end,
                Employee.is_deleted == False,
            )
        )
        hires_result = await db.execute(hires_query)
        new_hires = hires_result.scalar() or 0

        # Get terminations
        terms_query = select(func.count()).where(
            and_(
                Employee.termination_date >= period_start,
                Employee.termination_date < period_end,
                Employee.is_deleted == False,
            )
        )
        terms_result = await db.execute(terms_query)
        terminations = terms_result.scalar() or 0

        # Get total employees at end of period
        total_query = select(func.count()).where(
            and_(
                Employee.hire_date < period_end,
                or_(
                    Employee.termination_date >= period_end,
                    Employee.termination_date.is_(None),
                ),
                Employee.is_deleted == False,
            )
        )
        total_result = await db.execute(total_query)
        total_employees = total_result.scalar() or 0

        trends.append(
            EmployeeTrends(
                period=period_label,
                new_hires=new_hires,
                terminations=terminations,
                net_change=new_hires - terminations,
                total_employees=total_employees,
            )
        )

    return trends


@router.get("/gender-diversity", response_model=List[GenderDiversity])
@cached(key_prefix="analytics_gender_div", ttl=600)
async def get_gender_diversity(
    dept_no: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Get gender diversity statistics.

    Args:
        dept_no: Filter by department
        db: Database session

    Returns:
        Gender diversity data
    """
    # Build query
    query = select(Employee).where(
        and_(Employee.is_deleted == False, Employee.status == EmploymentStatus.Active)
    )

    if dept_no:
        query = (
            query.join(DeptEmp, Employee.emp_no == DeptEmp.emp_no)
            .where(
                and_(
                    DeptEmp.dept_no == dept_no,
                    DeptEmp.to_date == date(9999, 12, 31),
                    DeptEmp.is_deleted == False,
                )
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

    diversity_data = []
    for row in rows:
        diversity_data.append(
            GenderDiversity(
                gender=str(row.gender.value if row.gender else "Unknown"),
                count=row.count,
                percentage=round((row.count / total) * 100, 2),
                avg_salary=row.avg_salary,
            )
        )

    return diversity_data


@router.get("/title-distribution", response_model=List[TitleDistribution])
@cached(key_prefix="analytics_title_dist", ttl=600)
async def get_title_distribution(
    dept_no: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Get distribution of job titles.

    Args:
        dept_no: Filter by department
        db: Database session

    Returns:
        Title distribution
    """
    from app.models.title import Title

    # Build query
    query = select(Title).where(
        and_(Title.to_date == date(9999, 12, 31), Title.is_deleted == False)
    )

    if dept_no:
        query = (
            query.join(DeptEmp, Title.emp_no == DeptEmp.emp_no)
            .where(
                and_(
                    DeptEmp.dept_no == dept_no,
                    DeptEmp.to_date == date(9999, 12, 31),
                    DeptEmp.is_deleted == False,
                )
            )
        )

    # Get total count
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 1

    # Get title distribution with salary
    title_query = (
        select(
            Title.title,
            func.count(Title.id).label("count"),
            func.avg(Salary.salary).label("avg_salary"),
        )
        .select_from(query.subquery().alias("t"))
        .outerjoin(
            Salary,
            and_(
                Salary.emp_no == Title.emp_no,
                Salary.to_date == date(9999, 12, 31),
                Salary.is_deleted == False,
            ),
        )
        .group_by(Title.title)
        .order_by(desc(func.count(Title.id)))
    )

    result = await db.execute(title_query)
    rows = result.all()

    title_data = []
    for row in rows:
        title_data.append(
            TitleDistribution(
                title=row.title,
                count=row.count,
                percentage=round((row.count / total) * 100, 2),
                avg_salary=row.avg_salary,
            )
        )

    return title_data


@router.get("/summary")
@cached(key_prefix="analytics_summary", ttl=600)
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Get overall analytics summary.

    Args:
        db: Database session

    Returns:
        Analytics summary
    """
    # Total employees
    total_emp_query = select(func.count()).where(
        and_(Employee.is_deleted == False, Employee.status == EmploymentStatus.Active)
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
        func.avg(func.extract("days", func.current_date() - Employee.hire_date))
    ).where(and_(Employee.is_deleted == False, Employee.status == EmploymentStatus.Active))
    avg_tenure_result = await db.execute(avg_tenure_query)
    avg_tenure_days = avg_tenure_result.scalar()

    return {
        "total_employees": total_employees or 0,
        "total_departments": total_departments or 0,
        "avg_salary": float(avg_salary) if avg_salary else None,
        "total_payroll": float(total_payroll) if total_payroll else None,
        "avg_tenure_days": float(avg_tenure_days) if avg_tenure_days else None,
        "avg_tenure_years": round(float(avg_tenure_days) / 365, 2) if avg_tenure_days else None,
    }
