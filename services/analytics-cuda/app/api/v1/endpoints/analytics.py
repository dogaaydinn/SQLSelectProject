"""
Analytics API Endpoints
GPU-accelerated salary analytics
"""

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.cuda.gpu_analytics import gpu_analytics
from app.schemas.analytics import (
    SalaryStatistics,
    DepartmentStatistics,
    PerformanceMetrics,
    OutlierDetectionRequest,
    OutlierDetectionResponse,
    GrowthRateRequest,
    GrowthRateResponse,
    TrendAnalysisRequest,
    TrendAnalysisResponse,
    AnalyticsSummary,
)
from app.core.logging import logger

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Get summary of analytics capabilities and GPU status.

    Returns:
        Analytics capabilities summary
    """
    # Get counts from database
    from app.models.salary import Salary
    from app.models.department import Department

    total_employees_query = select(Salary.emp_no).distinct()
    total_depts_query = select(Department.dept_no).distinct()

    emp_result = await db.execute(total_employees_query)
    dept_result = await db.execute(total_depts_query)

    total_employees = len(emp_result.scalars().all())
    total_departments = len(dept_result.scalars().all())

    performance_metrics = gpu_analytics.get_performance_metrics()

    return AnalyticsSummary(
        total_employees=total_employees,
        total_departments=total_departments,
        gpu_accelerated=performance_metrics["mode"] == "GPU",
        available_operations=[
            "salary_statistics",
            "department_statistics",
            "outlier_detection",
            "growth_rate_analysis",
            "correlation_analysis",
            "trend_analysis",
        ],
        performance_metrics=PerformanceMetrics(**performance_metrics),
    )


@router.get("/salary/statistics", response_model=SalaryStatistics)
async def get_salary_statistics(
    current_only: bool = Query(True, description="Only current salaries"),
    department_id: Optional[str] = Query(None, description="Filter by department"),
    db: AsyncSession = Depends(get_db),
):
    """
    Compute comprehensive salary statistics using GPU acceleration.

    Args:
        current_only: Only include current salaries
        department_id: Filter by department
        db: Database session

    Returns:
        Comprehensive salary statistics
    """
    from app.models.salary import Salary
    from app.models.dept_emp import DeptEmp

    # Build query
    query = select(Salary.salary).where(Salary.is_deleted == False)

    if current_only:
        query = query.where(Salary.to_date == date(9999, 12, 31))

    if department_id:
        query = (
            query
            .join(DeptEmp, Salary.emp_no == DeptEmp.emp_no)
            .where(
                and_(
                    DeptEmp.dept_no == department_id,
                    DeptEmp.to_date == date(9999, 12, 31) if current_only else True,
                )
            )
        )

    # Execute query
    result = await db.execute(query)
    salaries = [float(s) for s in result.scalars().all()]

    if not salaries:
        raise HTTPException(status_code=404, detail="No salary data found")

    # Compute statistics using GPU
    stats = gpu_analytics.compute_salary_statistics(salaries)

    logger.info(
        f"Computed salary statistics for {len(salaries)} records "
        f"(mode: {gpu_analytics.use_gpu and 'GPU' or 'CPU'})"
    )

    return SalaryStatistics(**stats)


@router.get("/salary/by-department", response_model=List[DepartmentStatistics])
async def get_department_salary_statistics(
    current_only: bool = Query(True, description="Only current salaries"),
    db: AsyncSession = Depends(get_db),
):
    """
    Compute salary statistics grouped by department using GPU acceleration.

    Args:
        current_only: Only include current salaries
        db: Database session

    Returns:
        List of department statistics
    """
    from app.models.salary import Salary
    from app.models.dept_emp import DeptEmp
    from app.models.department import Department

    # Build query
    query = (
        select(Salary.salary, DeptEmp.dept_no, Department.dept_name)
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

    # Execute query
    result = await db.execute(query)
    rows = result.all()

    if not rows:
        raise HTTPException(status_code=404, detail="No department salary data found")

    # Prepare data for GPU processing
    salaries = [float(row[0]) for row in rows]
    dept_ids_map = {}
    dept_names = {}

    for idx, row in enumerate(rows):
        dept_no = row[1]
        dept_name = row[2]

        if dept_no not in dept_ids_map:
            dept_ids_map[dept_no] = len(dept_ids_map)
            dept_names[dept_no] = dept_name

    dept_ids = [dept_ids_map[row[1]] for row in rows]

    # Compute department statistics using GPU
    dept_stats = gpu_analytics.compute_department_statistics(salaries, dept_ids)

    # Convert back to response format
    result_list = []
    for dept_no, stats in dept_stats.items():
        # Find original department number
        original_dept_no = [k for k, v in dept_ids_map.items() if v == dept_no][0]

        result_list.append(
            DepartmentStatistics(
                dept_id=dept_no,
                dept_name=dept_names.get(original_dept_no),
                **stats,
            )
        )

    logger.info(
        f"Computed statistics for {len(result_list)} departments "
        f"(mode: {gpu_analytics.use_gpu and 'GPU' or 'CPU'})"
    )

    return result_list


@router.post("/salary/outliers", response_model=OutlierDetectionResponse)
async def detect_salary_outliers(
    request: OutlierDetectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Detect salary outliers using GPU-accelerated IQR or Z-score method.

    Args:
        request: Outlier detection request
        db: Database session

    Returns:
        Outlier detection results
    """
    from app.models.salary import Salary
    from app.models.employee import Employee

    # Build query
    query = (
        select(Salary.salary, Salary.emp_no, Employee.first_name, Employee.last_name)
        .join(Employee, Salary.emp_no == Employee.emp_no)
        .where(
            and_(
                Salary.to_date == date(9999, 12, 31),
                Salary.is_deleted == False,
                Employee.is_deleted == False,
            )
        )
    )

    if request.employee_ids:
        query = query.where(Salary.emp_no.in_(request.employee_ids))

    if request.department_id:
        from app.models.dept_emp import DeptEmp

        query = query.join(DeptEmp, Salary.emp_no == DeptEmp.emp_no).where(
            and_(
                DeptEmp.dept_no == request.department_id,
                DeptEmp.to_date == date(9999, 12, 31),
            )
        )

    # Execute query
    result = await db.execute(query)
    rows = result.all()

    if not rows:
        raise HTTPException(status_code=404, detail="No salary data found")

    salaries = [float(row[0]) for row in rows]

    # Detect outliers using GPU
    outlier_indices, outlier_values = gpu_analytics.detect_outliers(
        salaries,
        method=request.method,
    )

    # Build response
    outliers = []
    for idx in outlier_indices:
        row = rows[idx]
        outliers.append({
            "emp_no": row[1],
            "first_name": row[2],
            "last_name": row[3],
            "salary": float(row[0]),
        })

    logger.info(
        f"Detected {len(outliers)} outliers using {request.method} method "
        f"(mode: {gpu_analytics.use_gpu and 'GPU' or 'CPU'})"
    )

    return OutlierDetectionResponse(
        outlier_count=len(outliers),
        outliers=outliers,
        method=request.method,
    )


@router.post("/salary/growth-rate", response_model=GrowthRateResponse)
async def analyze_salary_growth(
    request: GrowthRateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze salary growth rates using GPU acceleration.

    Args:
        request: Growth rate analysis request
        db: Database session

    Returns:
        Growth rate analysis results
    """
    from app.models.salary import Salary
    from app.models.employee import Employee

    # Get salaries at start date
    start_query = (
        select(Salary.emp_no, Salary.salary, Employee.first_name, Employee.last_name)
        .join(Employee, Salary.emp_no == Employee.emp_no)
        .where(
            and_(
                Salary.from_date <= request.start_date,
                Salary.to_date >= request.start_date,
                Salary.is_deleted == False,
            )
        )
    )

    # Get salaries at end date
    end_query = (
        select(Salary.emp_no, Salary.salary)
        .where(
            and_(
                Salary.from_date <= request.end_date,
                Salary.to_date >= request.end_date,
                Salary.is_deleted == False,
            )
        )
    )

    if request.employee_ids:
        start_query = start_query.where(Salary.emp_no.in_(request.employee_ids))
        end_query = end_query.where(Salary.emp_no.in_(request.employee_ids))

    # Execute queries
    start_result = await db.execute(start_query)
    end_result = await db.execute(end_query)

    start_salaries = {row[0]: (float(row[1]), row[2], row[3]) for row in start_result.all()}
    end_salaries = {row[0]: float(row[1]) for row in end_result.all()}

    # Match employees present in both periods
    common_employees = set(start_salaries.keys()) & set(end_salaries.keys())

    if not common_employees:
        raise HTTPException(status_code=404, detail="No matching salary data found")

    # Prepare data for GPU
    previous_sal = [start_salaries[emp][0] for emp in common_employees]
    current_sal = [end_salaries[emp] for emp in common_employees]

    # Compute growth rates using GPU
    growth_rates = gpu_analytics.compute_salary_growth(current_sal, previous_sal)

    # Build response
    growth_by_employee = []
    for idx, emp_no in enumerate(common_employees):
        first_name, last_name = start_salaries[emp_no][1], start_salaries[emp_no][2]
        growth_by_employee.append({
            "emp_no": emp_no,
            "first_name": first_name,
            "last_name": last_name,
            "start_salary": previous_sal[idx],
            "end_salary": current_sal[idx],
            "growth_rate": growth_rates[idx],
        })

    # Sort by growth rate descending
    growth_by_employee.sort(key=lambda x: x["growth_rate"], reverse=True)

    import statistics

    avg_growth = statistics.mean(growth_rates)
    median_growth = statistics.median(growth_rates)

    logger.info(
        f"Analyzed growth rates for {len(common_employees)} employees "
        f"(mode: {gpu_analytics.use_gpu and 'GPU' or 'CPU'})"
    )

    return GrowthRateResponse(
        average_growth_rate=avg_growth,
        median_growth_rate=median_growth,
        growth_by_employee=growth_by_employee,
    )


@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics():
    """
    Get GPU performance metrics and status.

    Returns:
        GPU performance metrics
    """
    metrics = gpu_analytics.get_performance_metrics()
    return PerformanceMetrics(**metrics)
