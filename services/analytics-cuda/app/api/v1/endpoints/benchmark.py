"""
Performance Benchmarking Endpoints
Compare GPU vs CPU performance for analytics operations
"""

import time
from typing import Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import numpy as np

from app.core.database import get_db
from app.cuda.gpu_analytics import gpu_analytics
from app.core.logging import logger

router = APIRouter()


async def _generate_sample_data(db: AsyncSession, size: int) -> list:
    """Generate sample salary data for benchmarking."""
    from app.models.salary import Salary

    query = select(Salary.salary).where(Salary.is_deleted == False).limit(size)
    result = await db.execute(query)
    salaries = [float(s) for s in result.scalars().all()]

    # If not enough data, replicate to reach desired size
    while len(salaries) < size:
        salaries.extend(salaries[:min(len(salaries), size - len(salaries))])

    return salaries[:size]


@router.get("/statistics")
async def benchmark_statistics(
    data_size: int = Query(10000, ge=1000, le=1000000),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Benchmark salary statistics computation (GPU vs CPU).

    Args:
        data_size: Number of salary records to process
        db: Database session

    Returns:
        Benchmark results with speedup
    """
    salaries = await _generate_sample_data(db, data_size)

    # GPU benchmark
    gpu_available = gpu_analytics.use_gpu
    gpu_time = None
    gpu_result = None

    if gpu_available:
        # Force GPU mode
        original_use_gpu = gpu_analytics.use_gpu
        gpu_analytics.use_gpu = True

        start = time.perf_counter()
        gpu_result = gpu_analytics.compute_salary_statistics(salaries)
        gpu_time = (time.perf_counter() - start) * 1000  # Convert to ms

        gpu_analytics.use_gpu = original_use_gpu

    # CPU benchmark
    original_use_gpu = gpu_analytics.use_gpu
    gpu_analytics.use_gpu = False

    start = time.perf_counter()
    cpu_result = gpu_analytics.compute_salary_statistics(salaries)
    cpu_time = (time.perf_counter() - start) * 1000  # Convert to ms

    gpu_analytics.use_gpu = original_use_gpu

    # Calculate speedup
    speedup = cpu_time / gpu_time if gpu_time else None

    logger.info(
        f"Statistics benchmark - Data size: {data_size}, "
        f"GPU: {gpu_time:.2f}ms, CPU: {cpu_time:.2f}ms, "
        f"Speedup: {speedup:.2f}x" if speedup else f"CPU only: {cpu_time:.2f}ms"
    )

    return {
        "operation": "salary_statistics",
        "data_size": data_size,
        "gpu_available": gpu_available,
        "gpu_time_ms": gpu_time,
        "cpu_time_ms": cpu_time,
        "speedup": speedup,
        "result_sample": {
            "mean": cpu_result["mean"],
            "median": cpu_result["median"],
            "std": cpu_result["std"],
        },
    }


@router.get("/aggregation")
async def benchmark_aggregation(
    data_size: int = Query(10000, ge=1000, le=1000000),
    num_departments: int = Query(10, ge=2, le=100),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Benchmark department aggregation (GPU vs CPU).

    Args:
        data_size: Number of salary records
        num_departments: Number of departments
        db: Database session

    Returns:
        Benchmark results
    """
    salaries = await _generate_sample_data(db, data_size)
    dept_ids = np.random.randint(0, num_departments, size=data_size).tolist()

    # GPU benchmark
    gpu_available = gpu_analytics.use_gpu
    gpu_time = None

    if gpu_available:
        original_use_gpu = gpu_analytics.use_gpu
        gpu_analytics.use_gpu = True

        start = time.perf_counter()
        gpu_result = gpu_analytics.compute_department_statistics(salaries, dept_ids)
        gpu_time = (time.perf_counter() - start) * 1000

        gpu_analytics.use_gpu = original_use_gpu

    # CPU benchmark
    original_use_gpu = gpu_analytics.use_gpu
    gpu_analytics.use_gpu = False

    start = time.perf_counter()
    cpu_result = gpu_analytics.compute_department_statistics(salaries, dept_ids)
    cpu_time = (time.perf_counter() - start) * 1000

    gpu_analytics.use_gpu = original_use_gpu

    speedup = cpu_time / gpu_time if gpu_time else None

    logger.info(
        f"Aggregation benchmark - Data size: {data_size}, Depts: {num_departments}, "
        f"GPU: {gpu_time:.2f}ms, CPU: {cpu_time:.2f}ms, "
        f"Speedup: {speedup:.2f}x" if speedup else f"CPU only: {cpu_time:.2f}ms"
    )

    return {
        "operation": "department_aggregation",
        "data_size": data_size,
        "num_departments": num_departments,
        "gpu_available": gpu_available,
        "gpu_time_ms": gpu_time,
        "cpu_time_ms": cpu_time,
        "speedup": speedup,
    }


@router.get("/outlier-detection")
async def benchmark_outlier_detection(
    data_size: int = Query(10000, ge=1000, le=1000000),
    method: str = Query("iqr", regex="^(iqr|zscore)$"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Benchmark outlier detection (GPU vs CPU).

    Args:
        data_size: Number of salary records
        method: Detection method (iqr or zscore)
        db: Database session

    Returns:
        Benchmark results
    """
    salaries = await _generate_sample_data(db, data_size)

    # GPU benchmark
    gpu_available = gpu_analytics.use_gpu
    gpu_time = None
    gpu_outliers = None

    if gpu_available:
        original_use_gpu = gpu_analytics.use_gpu
        gpu_analytics.use_gpu = True

        start = time.perf_counter()
        gpu_indices, gpu_values = gpu_analytics.detect_outliers(salaries, method)
        gpu_time = (time.perf_counter() - start) * 1000
        gpu_outliers = len(gpu_indices)

        gpu_analytics.use_gpu = original_use_gpu

    # CPU benchmark
    original_use_gpu = gpu_analytics.use_gpu
    gpu_analytics.use_gpu = False

    start = time.perf_counter()
    cpu_indices, cpu_values = gpu_analytics.detect_outliers(salaries, method)
    cpu_time = (time.perf_counter() - start) * 1000
    cpu_outliers = len(cpu_indices)

    gpu_analytics.use_gpu = original_use_gpu

    speedup = cpu_time / gpu_time if gpu_time else None

    logger.info(
        f"Outlier detection benchmark - Data size: {data_size}, Method: {method}, "
        f"GPU: {gpu_time:.2f}ms, CPU: {cpu_time:.2f}ms, "
        f"Speedup: {speedup:.2f}x" if speedup else f"CPU only: {cpu_time:.2f}ms"
    )

    return {
        "operation": f"outlier_detection_{method}",
        "data_size": data_size,
        "gpu_available": gpu_available,
        "gpu_time_ms": gpu_time,
        "cpu_time_ms": cpu_time,
        "speedup": speedup,
        "outliers_detected": cpu_outliers,
    }


@router.get("/growth-rate")
async def benchmark_growth_rate(
    data_size: int = Query(10000, ge=1000, le=1000000),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Benchmark salary growth rate calculation (GPU vs CPU).

    Args:
        data_size: Number of salary records
        db: Database session

    Returns:
        Benchmark results
    """
    current_salaries = await _generate_sample_data(db, data_size)
    # Simulate previous salaries with 5% average decrease
    previous_salaries = [s * 0.95 for s in current_salaries]

    # GPU benchmark
    gpu_available = gpu_analytics.use_gpu
    gpu_time = None

    if gpu_available:
        original_use_gpu = gpu_analytics.use_gpu
        gpu_analytics.use_gpu = True

        start = time.perf_counter()
        gpu_result = gpu_analytics.compute_salary_growth(current_salaries, previous_salaries)
        gpu_time = (time.perf_counter() - start) * 1000

        gpu_analytics.use_gpu = original_use_gpu

    # CPU benchmark
    original_use_gpu = gpu_analytics.use_gpu
    gpu_analytics.use_gpu = False

    start = time.perf_counter()
    cpu_result = gpu_analytics.compute_salary_growth(current_salaries, previous_salaries)
    cpu_time = (time.perf_counter() - start) * 1000

    gpu_analytics.use_gpu = original_use_gpu

    speedup = cpu_time / gpu_time if gpu_time else None

    logger.info(
        f"Growth rate benchmark - Data size: {data_size}, "
        f"GPU: {gpu_time:.2f}ms, CPU: {cpu_time:.2f}ms, "
        f"Speedup: {speedup:.2f}x" if speedup else f"CPU only: {cpu_time:.2f}ms"
    )

    return {
        "operation": "salary_growth_rate",
        "data_size": data_size,
        "gpu_available": gpu_available,
        "gpu_time_ms": gpu_time,
        "cpu_time_ms": cpu_time,
        "speedup": speedup,
    }


@router.get("/comprehensive")
async def comprehensive_benchmark(
    data_size: int = Query(10000, ge=1000, le=100000),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Run comprehensive benchmark suite across all operations.

    Args:
        data_size: Number of salary records
        db: Database session

    Returns:
        Comprehensive benchmark results
    """
    results = {}

    # Statistics
    stats_result = await benchmark_statistics(data_size, db)
    results["statistics"] = stats_result

    # Aggregation
    agg_result = await benchmark_aggregation(data_size, 10, db)
    results["aggregation"] = agg_result

    # Outlier detection (IQR)
    outlier_result = await benchmark_outlier_detection(data_size, "iqr", db)
    results["outlier_detection"] = outlier_result

    # Growth rate
    growth_result = await benchmark_growth_rate(data_size, db)
    results["growth_rate"] = growth_result

    # Calculate average speedup
    speedups = [
        r["speedup"] for r in results.values()
        if r.get("speedup") is not None
    ]
    avg_speedup = sum(speedups) / len(speedups) if speedups else None

    logger.info(
        f"Comprehensive benchmark completed - "
        f"Data size: {data_size}, Average speedup: {avg_speedup:.2f}x"
        if avg_speedup else f"Data size: {data_size}, CPU only mode"
    )

    return {
        "data_size": data_size,
        "gpu_available": gpu_analytics.use_gpu,
        "average_speedup": avg_speedup,
        "operations": results,
    }
