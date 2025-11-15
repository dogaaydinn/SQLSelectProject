"""
Analytics Schemas
Request/Response models for CUDA analytics API
"""

from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel, Field


class SalaryStatistics(BaseModel):
    """Comprehensive salary statistics."""
    count: int
    mean: float
    median: float
    std: float
    min: float
    max: float
    q25: float = Field(..., description="25th percentile")
    q75: float = Field(..., description="75th percentile")
    variance: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None


class DepartmentStatistics(BaseModel):
    """Department-level salary statistics."""
    dept_id: int
    dept_name: Optional[str] = None
    count: int
    mean: float
    median: float
    std: float
    min: float
    max: float


class PerformanceMetrics(BaseModel):
    """GPU performance metrics."""
    mode: str = Field(..., description="GPU or CPU")
    gpu_available: bool
    device_id: Optional[int] = None
    device_name: Optional[str] = None
    total_memory_gb: Optional[float] = None
    free_memory_gb: Optional[float] = None
    used_memory_gb: Optional[float] = None
    memory_utilization: Optional[float] = None


class OutlierDetectionRequest(BaseModel):
    """Request for outlier detection."""
    method: str = Field("iqr", description="Method: 'iqr' or 'zscore'")
    employee_ids: Optional[List[int]] = Field(None, description="Filter by employee IDs")
    department_id: Optional[str] = Field(None, description="Filter by department")


class OutlierDetectionResponse(BaseModel):
    """Response for outlier detection."""
    outlier_count: int
    outliers: List[Dict[str, Any]]
    method: str


class GrowthRateRequest(BaseModel):
    """Request for salary growth rate analysis."""
    start_date: date
    end_date: date
    department_id: Optional[str] = None
    employee_ids: Optional[List[int]] = None


class GrowthRateResponse(BaseModel):
    """Response for salary growth rate analysis."""
    average_growth_rate: float
    median_growth_rate: float
    growth_by_employee: List[Dict[str, Any]]


class CorrelationRequest(BaseModel):
    """Request for correlation analysis."""
    metric: str = Field(..., description="Metric to correlate with salary (e.g., 'tenure', 'age')")
    department_id: Optional[str] = None


class CorrelationResponse(BaseModel):
    """Response for correlation analysis."""
    correlation: float
    p_value: Optional[float] = None
    sample_size: int


class TrendAnalysisRequest(BaseModel):
    """Request for time series trend analysis."""
    start_date: date
    end_date: date
    aggregation: str = Field("monthly", description="Aggregation: 'daily', 'weekly', 'monthly', 'yearly'")
    department_id: Optional[str] = None


class TrendAnalysisResponse(BaseModel):
    """Response for trend analysis."""
    trend: List[Dict[str, Any]]
    moving_average: List[float]
    growth_trend: str = Field(..., description="Trend direction: 'increasing', 'decreasing', 'stable'")


class BenchmarkRequest(BaseModel):
    """Request for performance benchmarking."""
    operation: str = Field(..., description="Operation to benchmark")
    data_size: int = Field(1000, description="Number of records")


class BenchmarkResponse(BaseModel):
    """Response for performance benchmarking."""
    operation: str
    data_size: int
    gpu_time_ms: Optional[float] = None
    cpu_time_ms: Optional[float] = None
    speedup: Optional[float] = None
    mode: str


class AnalyticsSummary(BaseModel):
    """Summary of analytics capabilities."""
    total_employees: int
    total_departments: int
    gpu_accelerated: bool
    available_operations: List[str]
    performance_metrics: PerformanceMetrics
