"""
Analytics Engine with GPU/CPU Support
Provides high-performance data analytics with automatic GPU/CPU selection
"""

import time
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
import numpy as np
from multiprocessing import Pool, cpu_count

from app.core.config import settings


class AnalyticsEngine:
    """
    High-performance analytics engine with GPU/CPU fallback.

    Automatically selects GPU (CUDA) or CPU processing based on availability.
    """

    def __init__(self):
        self.use_gpu = settings.should_use_gpu()
        self.batch_size = settings.BATCH_SIZE
        self.cpu_workers = settings.CPU_WORKERS or cpu_count()

        if self.use_gpu:
            self._init_gpu()

        print(f"Analytics Engine initialized: {'GPU' if self.use_gpu else 'CPU'} mode")

    def _init_gpu(self):
        """Initialize GPU resources."""
        try:
            import cupy as cp
            self.cp = cp
            self.gpu_device = cp.cuda.Device(settings.GPU_DEVICE_ID)
            print(f"GPU initialized: {self.gpu_device.compute_capability}")
        except Exception as e:
            print(f"GPU initialization failed: {e}, falling back to CPU")
            self.use_gpu = False

    # ==========================================
    # Aggregation Functions
    # ==========================================

    def aggregate_sum(self, data: List[float]) -> float:
        """
        Calculate sum of values.

        GPU: O(n) with parallel reduction
        CPU: O(n) with NumPy

        Args:
            data: List of numeric values

        Returns:
            Sum of all values
        """
        start_time = time.time()

        if not data:
            return 0.0

        if self.use_gpu and len(data) > 10000:
            arr = self.cp.array(data, dtype=self.cp.float64)
            result = float(self.cp.sum(arr))
        else:
            arr = np.array(data, dtype=np.float64)
            result = float(np.sum(arr))

        elapsed = time.time() - start_time
        if settings.ENABLE_PROFILING:
            print(f"Sum aggregation: {elapsed:.4f}s ({len(data)} records)")

        return result

    def aggregate_avg(self, data: List[float]) -> Optional[float]:
        """
        Calculate average of values.

        Args:
            data: List of numeric values

        Returns:
            Average value or None if empty
        """
        if not data:
            return None

        if self.use_gpu and len(data) > 10000:
            arr = self.cp.array(data, dtype=self.cp.float64)
            result = float(self.cp.mean(arr))
        else:
            arr = np.array(data, dtype=np.float64)
            result = float(np.mean(arr))

        return result

    def aggregate_min_max(self, data: List[float]) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate min and max values.

        Args:
            data: List of numeric values

        Returns:
            Tuple of (min, max) or (None, None) if empty
        """
        if not data:
            return None, None

        if self.use_gpu and len(data) > 10000:
            arr = self.cp.array(data, dtype=self.cp.float64)
            min_val = float(self.cp.min(arr))
            max_val = float(self.cp.max(arr))
        else:
            arr = np.array(data, dtype=np.float64)
            min_val = float(np.min(arr))
            max_val = float(np.max(arr))

        return min_val, max_val

    def aggregate_count(self, data: List[Any]) -> int:
        """
        Count number of elements.

        Args:
            data: List of values

        Returns:
            Count of elements
        """
        return len(data)

    # ==========================================
    # Statistical Functions
    # ==========================================

    def calculate_statistics(self, data: List[float]) -> Dict[str, Any]:
        """
        Calculate comprehensive statistics.

        Computes: count, sum, mean, min, max, std, variance

        Args:
            data: List of numeric values

        Returns:
            Dictionary of statistics
        """
        start_time = time.time()

        if not data:
            return {
                "count": 0,
                "sum": None,
                "mean": None,
                "min": None,
                "max": None,
                "std": None,
                "variance": None,
            }

        if self.use_gpu and len(data) > 10000:
            arr = self.cp.array(data, dtype=self.cp.float64)
            stats = {
                "count": len(data),
                "sum": float(self.cp.sum(arr)),
                "mean": float(self.cp.mean(arr)),
                "min": float(self.cp.min(arr)),
                "max": float(self.cp.max(arr)),
                "std": float(self.cp.std(arr)),
                "variance": float(self.cp.var(arr)),
            }
        else:
            arr = np.array(data, dtype=np.float64)
            stats = {
                "count": len(data),
                "sum": float(np.sum(arr)),
                "mean": float(np.mean(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "std": float(np.std(arr)),
                "variance": float(np.var(arr)),
            }

        elapsed = time.time() - start_time
        if settings.ENABLE_PROFILING:
            print(f"Statistics calculation: {elapsed:.4f}s ({len(data)} records)")

        return stats

    def calculate_percentiles(
        self,
        data: List[float],
        percentiles: List[float] = [25, 50, 75, 90, 95, 99],
    ) -> Dict[str, float]:
        """
        Calculate percentiles.

        Args:
            data: List of numeric values
            percentiles: List of percentile values (0-100)

        Returns:
            Dictionary mapping percentile to value
        """
        if not data:
            return {}

        if self.use_gpu and len(data) > 10000:
            arr = self.cp.array(data, dtype=self.cp.float64)
            result = {
                f"p{p}": float(self.cp.percentile(arr, p))
                for p in percentiles
            }
        else:
            arr = np.array(data, dtype=np.float64)
            result = {
                f"p{p}": float(np.percentile(arr, p))
                for p in percentiles
            }

        return result

    def calculate_histogram(
        self,
        data: List[float],
        bins: int = 10,
    ) -> Dict[str, Any]:
        """
        Calculate histogram distribution.

        Args:
            data: List of numeric values
            bins: Number of bins

        Returns:
            Dictionary with histogram data
        """
        if not data:
            return {"bins": [], "counts": []}

        if self.use_gpu and len(data) > 10000:
            arr = self.cp.array(data, dtype=self.cp.float64)
            counts, edges = self.cp.histogram(arr, bins=bins)
            counts = self.cp.asnumpy(counts).tolist()
            edges = self.cp.asnumpy(edges).tolist()
        else:
            arr = np.array(data, dtype=np.float64)
            counts, edges = np.histogram(arr, bins=bins)
            counts = counts.tolist()
            edges = edges.tolist()

        return {
            "bins": edges,
            "counts": counts,
        }

    # ==========================================
    # Group By Operations
    # ==========================================

    def group_by_aggregate(
        self,
        data: List[Tuple[Any, float]],
        operation: str = "sum",
    ) -> Dict[Any, float]:
        """
        Group by first element and aggregate second element.

        Args:
            data: List of (key, value) tuples
            operation: 'sum', 'avg', 'min', 'max', 'count'

        Returns:
            Dictionary mapping keys to aggregated values
        """
        if not data:
            return {}

        # Group data by key
        groups = {}
        for key, value in data:
            if key not in groups:
                groups[key] = []
            groups[key].append(value)

        # Apply operation to each group
        result = {}
        for key, values in groups.items():
            if operation == "sum":
                result[key] = self.aggregate_sum(values)
            elif operation == "avg":
                result[key] = self.aggregate_avg(values)
            elif operation == "min":
                result[key] = self.aggregate_min_max(values)[0]
            elif operation == "max":
                result[key] = self.aggregate_min_max(values)[1]
            elif operation == "count":
                result[key] = len(values)
            else:
                raise ValueError(f"Unknown operation: {operation}")

        return result

    # ==========================================
    # Time Series Analysis
    # ==========================================

    def moving_average(
        self,
        data: List[float],
        window: int = 7,
    ) -> List[float]:
        """
        Calculate moving average.

        Args:
            data: Time series data
            window: Window size

        Returns:
            Moving average values
        """
        if not data or len(data) < window:
            return data

        if self.use_gpu and len(data) > 10000:
            arr = self.cp.array(data, dtype=self.cp.float64)
            # Implement convolution-based moving average
            kernel = self.cp.ones(window) / window
            result = self.cp.convolve(arr, kernel, mode='valid')
            return self.cp.asnumpy(result).tolist()
        else:
            arr = np.array(data, dtype=np.float64)
            kernel = np.ones(window) / window
            result = np.convolve(arr, kernel, mode='valid')
            return result.tolist()

    # ==========================================
    # Performance Benchmarking
    # ==========================================

    def benchmark(self, data_size: int = 1000000) -> Dict[str, float]:
        """
        Benchmark analytics operations.

        Args:
            data_size: Number of elements to process

        Returns:
            Timing results for various operations
        """
        # Generate test data
        data = np.random.randn(data_size).tolist()

        results = {}

        # Benchmark sum
        start = time.time()
        self.aggregate_sum(data)
        results["sum"] = time.time() - start

        # Benchmark avg
        start = time.time()
        self.aggregate_avg(data)
        results["avg"] = time.time() - start

        # Benchmark statistics
        start = time.time()
        self.calculate_statistics(data)
        results["statistics"] = time.time() - start

        # Benchmark percentiles
        start = time.time()
        self.calculate_percentiles(data)
        results["percentiles"] = time.time() - start

        results["mode"] = "GPU" if self.use_gpu else "CPU"
        results["data_size"] = data_size

        return results


# Global analytics engine instance
analytics_engine = AnalyticsEngine()
