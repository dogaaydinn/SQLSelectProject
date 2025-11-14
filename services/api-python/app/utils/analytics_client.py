"""
Analytics Service Client
Communicates with CUDA analytics service for GPU-accelerated operations
"""

from typing import List, Dict, Any, Optional
import httpx
from decimal import Decimal

from app.core.config import settings


class AnalyticsClient:
    """
    Client for communicating with the analytics CUDA service.

    Provides high-level interface for GPU-accelerated analytics operations.
    """

    def __init__(self, base_url: str = "http://analytics-cuda:8001"):
        """
        Initialize analytics client.

        Args:
            base_url: Base URL of the analytics service
        """
        self.base_url = base_url
        self.timeout = 30.0  # seconds

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if analytics service is healthy.

        Returns:
            Health status
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return response.json()
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "error": str(e),
                }

    async def aggregate(
        self,
        data: List[float],
        operation: str = "sum",
    ) -> Dict[str, Any]:
        """
        Perform aggregation operation.

        Args:
            data: Numeric data to aggregate
            operation: 'sum', 'avg', 'min', 'max', 'count'

        Returns:
            Aggregation result
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/aggregate",
                json={"data": data, "operation": operation},
            )
            response.raise_for_status()
            return response.json()

    async def aggregate_all(self, data: List[float]) -> Dict[str, Any]:
        """
        Calculate all aggregations at once.

        Args:
            data: Numeric data

        Returns:
            All aggregation results (count, sum, avg, min, max)
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/aggregate/all",
                json=data,
            )
            response.raise_for_status()
            return response.json()

    async def calculate_statistics(
        self,
        data: List[float],
        include_percentiles: bool = True,
        include_histogram: bool = False,
        histogram_bins: int = 10,
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive statistics.

        Args:
            data: Numeric data
            include_percentiles: Include percentile calculations
            include_histogram: Include histogram
            histogram_bins: Number of histogram bins

        Returns:
            Statistics including mean, std, min, max, etc.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/statistics",
                json={
                    "data": data,
                    "include_percentiles": include_percentiles,
                    "include_histogram": include_histogram,
                    "histogram_bins": histogram_bins,
                },
            )
            response.raise_for_status()
            return response.json()

    async def calculate_percentiles(
        self,
        data: List[float],
        percentiles: List[float] = [25, 50, 75, 90, 95, 99],
    ) -> Dict[str, float]:
        """
        Calculate percentiles.

        Args:
            data: Numeric data
            percentiles: List of percentile values (0-100)

        Returns:
            Dictionary mapping percentile to value
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/percentiles",
                params={"percentiles": percentiles},
                json=data,
            )
            response.raise_for_status()
            return response.json()

    async def group_by_aggregate(
        self,
        data: List[Dict[str, Any]],
        key_field: str,
        value_field: str,
        operation: str = "sum",
    ) -> Dict[str, Any]:
        """
        Group by key and aggregate values.

        Args:
            data: List of dictionaries with key and value fields
            key_field: Field name for grouping
            value_field: Field name for aggregation
            operation: Aggregation operation

        Returns:
            Grouped aggregation results
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/group-by",
                json={
                    "data": data,
                    "key_field": key_field,
                    "value_field": value_field,
                    "operation": operation,
                },
            )
            response.raise_for_status()
            return response.json()

    async def moving_average(
        self,
        data: List[float],
        window: int = 7,
    ) -> Dict[str, Any]:
        """
        Calculate moving average.

        Args:
            data: Time series data
            window: Window size

        Returns:
            Moving average values
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/moving-average",
                json={"data": data, "window": window},
            )
            response.raise_for_status()
            return response.json()

    async def benchmark(
        self,
        data_size: int = 1000000,
        iterations: int = 10,
    ) -> Dict[str, Any]:
        """
        Run performance benchmark.

        Args:
            data_size: Number of elements to process
            iterations: Number of iterations

        Returns:
            Benchmark results
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/benchmark",
                json={"data_size": data_size, "iterations": iterations},
            )
            response.raise_for_status()
            return response.json()

    # ==========================================
    # Helper Methods for Common Use Cases
    # ==========================================

    async def salary_statistics(
        self,
        salaries: List[Decimal],
    ) -> Dict[str, Any]:
        """
        Calculate salary statistics.

        Args:
            salaries: List of salary values

        Returns:
            Statistics optimized for salary analysis
        """
        salary_floats = [float(s) for s in salaries]
        return await self.calculate_statistics(
            salary_floats,
            include_percentiles=True,
        )

    async def department_aggregates(
        self,
        department_salaries: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculate department salary aggregates.

        Args:
            department_salaries: List of {"dept_no": str, "salary": float}

        Returns:
            Department-wise salary aggregates
        """
        return await self.group_by_aggregate(
            department_salaries,
            key_field="dept_no",
            value_field="salary",
            operation="avg",
        )


# Global analytics client instance
analytics_client = AnalyticsClient()
