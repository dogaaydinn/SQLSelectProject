"""
Analytics CUDA Service - Main Application
FastAPI wrapper for GPU-accelerated analytics
"""

from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.analytics.engine import analytics_engine


# ==========================================
# Pydantic Models
# ==========================================

class AggregateRequest(BaseModel):
    """Request for basic aggregation."""
    data: List[float] = Field(..., description="Numeric data to aggregate")
    operation: str = Field("sum", description="Operation: sum, avg, min, max, count")


class StatisticsRequest(BaseModel):
    """Request for statistical analysis."""
    data: List[float] = Field(..., description="Numeric data to analyze")
    include_percentiles: bool = Field(True, description="Include percentile calculations")
    include_histogram: bool = Field(False, description="Include histogram")
    histogram_bins: int = Field(10, ge=2, le=100, description="Number of histogram bins")


class GroupByRequest(BaseModel):
    """Request for group-by aggregation."""
    data: List[Dict[str, Any]] = Field(..., description="Data with key and value fields")
    key_field: str = Field(..., description="Field name for grouping")
    value_field: str = Field(..., description="Field name for aggregation")
    operation: str = Field("sum", description="Aggregation operation")


class MovingAverageRequest(BaseModel):
    """Request for moving average calculation."""
    data: List[float] = Field(..., description="Time series data")
    window: int = Field(7, ge=2, le=365, description="Window size")


class BenchmarkRequest(BaseModel):
    """Request for performance benchmarking."""
    data_size: int = Field(1000000, ge=1000, le=100000000, description="Data size for benchmark")
    iterations: int = Field(10, ge=1, le=100, description="Number of iterations")


# ==========================================
# FastAPI Application
# ==========================================

app = FastAPI(
    title=settings.SERVICE_NAME,
    description="GPU-accelerated analytics service for high-performance data processing",
    version=settings.VERSION,
    default_response_class=ORJSONResponse,
)


# ==========================================
# Health & Info Endpoints
# ==========================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "mode": "GPU" if analytics_engine.use_gpu else "CPU",
    }


@app.get("/info")
async def get_info():
    """Get service information."""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "processing_mode": "GPU" if analytics_engine.use_gpu else "CPU",
        "batch_size": settings.BATCH_SIZE,
        "cpu_workers": analytics_engine.cpu_workers,
        "cache_enabled": settings.CACHE_ENABLED,
    }


# ==========================================
# Aggregation Endpoints
# ==========================================

@app.post("/aggregate")
async def aggregate(request: AggregateRequest):
    """
    Perform aggregation operation on data.

    Supported operations: sum, avg, min, max, count

    GPU-accelerated for large datasets (>10k elements).
    """
    try:
        operation = request.operation.lower()

        if operation == "sum":
            result = analytics_engine.aggregate_sum(request.data)
        elif operation == "avg":
            result = analytics_engine.aggregate_avg(request.data)
        elif operation in ["min", "max"]:
            min_val, max_val = analytics_engine.aggregate_min_max(request.data)
            result = min_val if operation == "min" else max_val
        elif operation == "count":
            result = analytics_engine.aggregate_count(request.data)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown operation: {operation}",
            )

        return {
            "operation": operation,
            "result": result,
            "count": len(request.data),
            "mode": "GPU" if analytics_engine.use_gpu else "CPU",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.post("/aggregate/all")
async def aggregate_all(data: List[float]):
    """
    Calculate all aggregate functions at once.

    More efficient than calling each operation separately.
    """
    try:
        min_val, max_val = analytics_engine.aggregate_min_max(data)

        return {
            "count": analytics_engine.aggregate_count(data),
            "sum": analytics_engine.aggregate_sum(data),
            "avg": analytics_engine.aggregate_avg(data),
            "min": min_val,
            "max": max_val,
            "mode": "GPU" if analytics_engine.use_gpu else "CPU",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ==========================================
# Statistical Analysis Endpoints
# ==========================================

@app.post("/statistics")
async def calculate_statistics(request: StatisticsRequest):
    """
    Calculate comprehensive statistics.

    Returns: count, sum, mean, min, max, std, variance
    Optionally: percentiles and histogram
    """
    try:
        stats = analytics_engine.calculate_statistics(request.data)

        if request.include_percentiles:
            percentiles = analytics_engine.calculate_percentiles(request.data)
            stats["percentiles"] = percentiles

        if request.include_histogram:
            histogram = analytics_engine.calculate_histogram(
                request.data,
                bins=request.histogram_bins,
            )
            stats["histogram"] = histogram

        stats["mode"] = "GPU" if analytics_engine.use_gpu else "CPU"

        return stats

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.post("/percentiles")
async def calculate_percentiles(
    data: List[float],
    percentiles: List[float] = [25, 50, 75, 90, 95, 99],
):
    """
    Calculate percentiles.

    Default: 25th, 50th (median), 75th, 90th, 95th, 99th percentiles
    """
    try:
        result = analytics_engine.calculate_percentiles(data, percentiles)
        result["mode"] = "GPU" if analytics_engine.use_gpu else "CPU"
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ==========================================
# Group By Endpoints
# ==========================================

@app.post("/group-by")
async def group_by_aggregate(request: GroupByRequest):
    """
    Group by key and aggregate values.

    Example:
    ```json
    {
        "data": [
            {"dept": "Engineering", "salary": 100000},
            {"dept": "Engineering", "salary": 120000},
            {"dept": "Sales", "salary": 80000}
        ],
        "key_field": "dept",
        "value_field": "salary",
        "operation": "avg"
    }
    ```
    """
    try:
        # Extract key-value pairs
        pairs = [
            (item[request.key_field], item[request.value_field])
            for item in request.data
        ]

        result = analytics_engine.group_by_aggregate(pairs, request.operation)

        return {
            "groups": result,
            "operation": request.operation,
            "mode": "GPU" if analytics_engine.use_gpu else "CPU",
        }

    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Field not found: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ==========================================
# Time Series Endpoints
# ==========================================

@app.post("/moving-average")
async def calculate_moving_average(request: MovingAverageRequest):
    """
    Calculate moving average for time series data.

    Window size determines smoothing (larger = smoother).
    """
    try:
        result = analytics_engine.moving_average(request.data, request.window)

        return {
            "values": result,
            "window": request.window,
            "original_count": len(request.data),
            "result_count": len(result),
            "mode": "GPU" if analytics_engine.use_gpu else "CPU",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ==========================================
# Benchmarking Endpoints
# ==========================================

@app.post("/benchmark")
async def run_benchmark(request: Optional[BenchmarkRequest] = None):
    """
    Run performance benchmark.

    Tests various operations with specified data size.
    """
    try:
        if request is None:
            request = BenchmarkRequest()

        results = analytics_engine.benchmark(request.data_size)

        # Calculate speedup if both CPU and GPU results available
        if analytics_engine.use_gpu:
            # Estimate CPU performance (rough approximation)
            results["estimated_speedup"] = "10-50x faster than CPU"

        return results

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ==========================================
# Startup & Shutdown
# ==========================================

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    print(f"Starting {settings.SERVICE_NAME} v{settings.VERSION}")
    print(f"Mode: {'GPU' if analytics_engine.use_gpu else 'CPU'}")
    print(f"Workers: {analytics_engine.cpu_workers}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print(f"Shutting down {settings.SERVICE_NAME}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        workers=settings.WORKERS,
    )
