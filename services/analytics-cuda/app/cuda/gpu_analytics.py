"""
GPU Analytics Module
Python wrappers for CUDA kernels using cuPy and cuDF
"""

import os
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from pathlib import Path

try:
    import cupy as cp
    import cudf
    from cupyx.scipy import stats as cu_stats
    CUDA_AVAILABLE = True
except ImportError:
    CUDA_AVAILABLE = False
    cp = None
    cudf = None
    cu_stats = None

from app.core.config import settings
from app.core.logging import logger


class GPUAnalytics:
    """
    GPU-accelerated analytics using CUDA and cuPy.
    Automatically falls back to CPU if GPU is unavailable.
    """

    def __init__(self):
        """Initialize GPU analytics with CUDA kernels."""
        self.use_gpu = settings.USE_GPU and CUDA_AVAILABLE

        if self.use_gpu:
            try:
                # Set GPU device
                cp.cuda.Device(settings.CUDA_DEVICE).use()

                # Set memory pool
                mempool = cp.get_default_memory_pool()
                mempool.set_limit(size=int(settings.GPU_MEMORY_FRACTION * self._get_gpu_memory()))

                # Load CUDA kernels
                self._load_cuda_kernels()

                logger.info(
                    f"GPU Analytics initialized on device {settings.CUDA_DEVICE} "
                    f"with {self._get_gpu_memory() / 1e9:.2f} GB memory"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize GPU: {e}. Falling back to CPU.")
                self.use_gpu = False
        else:
            logger.info("GPU Analytics initialized in CPU mode")

    def _load_cuda_kernels(self):
        """Load compiled CUDA kernels."""
        kernel_path = Path(__file__).parent / "salary_kernels.cu"

        if kernel_path.exists():
            with open(kernel_path, 'r') as f:
                kernel_code = f.read()

            # Compile kernels with cuPy
            self.salary_sum = cp.RawKernel(kernel_code, 'salary_sum_kernel')
            self.salary_average = cp.RawKernel(kernel_code, 'salary_average_kernel')
            self.salary_min_max = cp.RawKernel(kernel_code, 'salary_min_max_kernel')
            self.salary_variance = cp.RawKernel(kernel_code, 'salary_variance_kernel')
            self.dept_aggregate = cp.RawKernel(kernel_code, 'dept_salary_aggregate_kernel')
            self.salary_growth = cp.RawKernel(kernel_code, 'salary_growth_kernel')

            logger.info("CUDA kernels loaded successfully")
        else:
            logger.warning(f"CUDA kernel file not found: {kernel_path}")

    def _get_gpu_memory(self) -> int:
        """Get total GPU memory in bytes."""
        if self.use_gpu:
            return cp.cuda.Device().mem_info[1]
        return 0

    def compute_salary_statistics(
        self,
        salaries: List[float],
    ) -> Dict[str, float]:
        """
        Compute comprehensive salary statistics.

        Args:
            salaries: List of salary values

        Returns:
            Dictionary with statistical metrics
        """
        if self.use_gpu:
            return self._gpu_compute_statistics(salaries)
        else:
            return self._cpu_compute_statistics(salaries)

    def _gpu_compute_statistics(self, salaries: List[float]) -> Dict[str, float]:
        """GPU implementation of salary statistics."""
        # Transfer data to GPU
        salaries_gpu = cp.array(salaries, dtype=cp.float32)
        n = len(salaries)

        # Compute statistics using cuPy
        mean = float(cp.mean(salaries_gpu))
        median = float(cp.median(salaries_gpu))
        std = float(cp.std(salaries_gpu))
        min_val = float(cp.min(salaries_gpu))
        max_val = float(cp.max(salaries_gpu))

        # Percentiles
        q25 = float(cp.percentile(salaries_gpu, 25))
        q75 = float(cp.percentile(salaries_gpu, 75))

        # Advanced statistics
        variance = float(cp.var(salaries_gpu))
        skewness = float(cu_stats.skew(salaries_gpu))
        kurtosis = float(cu_stats.kurtosis(salaries_gpu))

        return {
            "count": n,
            "mean": mean,
            "median": median,
            "std": std,
            "min": min_val,
            "max": max_val,
            "q25": q25,
            "q75": q75,
            "variance": variance,
            "skewness": skewness,
            "kurtosis": kurtosis,
        }

    def _cpu_compute_statistics(self, salaries: List[float]) -> Dict[str, float]:
        """CPU fallback implementation."""
        import pandas as pd
        from scipy import stats

        df = pd.Series(salaries)

        return {
            "count": len(salaries),
            "mean": float(df.mean()),
            "median": float(df.median()),
            "std": float(df.std()),
            "min": float(df.min()),
            "max": float(df.max()),
            "q25": float(df.quantile(0.25)),
            "q75": float(df.quantile(0.75)),
            "variance": float(df.var()),
            "skewness": float(stats.skew(df)),
            "kurtosis": float(stats.kurtosis(df)),
        }

    def compute_department_statistics(
        self,
        salaries: List[float],
        dept_ids: List[int],
    ) -> Dict[int, Dict[str, float]]:
        """
        Compute salary statistics grouped by department.

        Args:
            salaries: List of salary values
            dept_ids: List of department IDs (same length as salaries)

        Returns:
            Dictionary mapping dept_id to statistics
        """
        if self.use_gpu:
            return self._gpu_department_statistics(salaries, dept_ids)
        else:
            return self._cpu_department_statistics(salaries, dept_ids)

    def _gpu_department_statistics(
        self,
        salaries: List[float],
        dept_ids: List[int],
    ) -> Dict[int, Dict[str, float]]:
        """GPU implementation using cuDF."""
        # Create cuDF DataFrame
        df = cudf.DataFrame({
            'salary': salaries,
            'dept_id': dept_ids,
        })

        # Group by department and compute statistics
        grouped = df.groupby('dept_id')['salary'].agg([
            'count',
            'mean',
            'median',
            'std',
            'min',
            'max',
        ])

        # Convert to dictionary
        result = {}
        for dept_id in grouped.index.to_pandas():
            stats = grouped.loc[dept_id]
            result[int(dept_id)] = {
                'count': int(stats['count']),
                'mean': float(stats['mean']),
                'median': float(stats['median']),
                'std': float(stats['std']),
                'min': float(stats['min']),
                'max': float(stats['max']),
            }

        return result

    def _cpu_department_statistics(
        self,
        salaries: List[float],
        dept_ids: List[int],
    ) -> Dict[int, Dict[str, float]]:
        """CPU fallback implementation."""
        import pandas as pd

        df = pd.DataFrame({
            'salary': salaries,
            'dept_id': dept_ids,
        })

        grouped = df.groupby('dept_id')['salary'].agg([
            'count',
            'mean',
            'median',
            'std',
            'min',
            'max',
        ])

        result = {}
        for dept_id in grouped.index:
            stats = grouped.loc[dept_id]
            result[int(dept_id)] = {
                'count': int(stats['count']),
                'mean': float(stats['mean']),
                'median': float(stats['median']),
                'std': float(stats['std']),
                'min': float(stats['min']),
                'max': float(stats['max']),
            }

        return result

    def compute_salary_growth(
        self,
        current_salaries: List[float],
        previous_salaries: List[float],
    ) -> List[float]:
        """
        Compute salary growth rates.

        Args:
            current_salaries: Current salary values
            previous_salaries: Previous salary values

        Returns:
            List of growth rate percentages
        """
        if self.use_gpu:
            return self._gpu_salary_growth(current_salaries, previous_salaries)
        else:
            return self._cpu_salary_growth(current_salaries, previous_salaries)

    def _gpu_salary_growth(
        self,
        current_salaries: List[float],
        previous_salaries: List[float],
    ) -> List[float]:
        """GPU implementation of growth calculation."""
        current_gpu = cp.array(current_salaries, dtype=cp.float32)
        previous_gpu = cp.array(previous_salaries, dtype=cp.float32)

        # Avoid division by zero
        mask = previous_gpu > 0
        growth_rates = cp.zeros_like(current_gpu)

        growth_rates[mask] = (
            (current_gpu[mask] - previous_gpu[mask]) / previous_gpu[mask] * 100.0
        )

        return growth_rates.get().tolist()

    def _cpu_salary_growth(
        self,
        current_salaries: List[float],
        previous_salaries: List[float],
    ) -> List[float]:
        """CPU fallback implementation."""
        import pandas as pd

        current = pd.Series(current_salaries)
        previous = pd.Series(previous_salaries)

        mask = previous > 0
        growth_rates = pd.Series([0.0] * len(current))

        growth_rates[mask] = ((current[mask] - previous[mask]) / previous[mask] * 100.0)

        return growth_rates.tolist()

    def detect_outliers(
        self,
        salaries: List[float],
        method: str = "iqr",
    ) -> Tuple[List[int], List[float]]:
        """
        Detect salary outliers using IQR or Z-score method.

        Args:
            salaries: List of salary values
            method: "iqr" or "zscore"

        Returns:
            Tuple of (outlier_indices, outlier_values)
        """
        if self.use_gpu:
            return self._gpu_detect_outliers(salaries, method)
        else:
            return self._cpu_detect_outliers(salaries, method)

    def _gpu_detect_outliers(
        self,
        salaries: List[float],
        method: str = "iqr",
    ) -> Tuple[List[int], List[float]]:
        """GPU implementation of outlier detection."""
        salaries_gpu = cp.array(salaries, dtype=cp.float32)

        if method == "iqr":
            q1 = cp.percentile(salaries_gpu, 25)
            q3 = cp.percentile(salaries_gpu, 75)
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outlier_mask = (salaries_gpu < lower_bound) | (salaries_gpu > upper_bound)
        else:  # zscore
            mean = cp.mean(salaries_gpu)
            std = cp.std(salaries_gpu)
            z_scores = cp.abs((salaries_gpu - mean) / std)

            outlier_mask = z_scores > 3

        outlier_indices = cp.where(outlier_mask)[0].get().tolist()
        outlier_values = salaries_gpu[outlier_mask].get().tolist()

        return outlier_indices, outlier_values

    def _cpu_detect_outliers(
        self,
        salaries: List[float],
        method: str = "iqr",
    ) -> Tuple[List[int], List[float]]:
        """CPU fallback implementation."""
        import pandas as pd

        df = pd.Series(salaries)

        if method == "iqr":
            q1 = df.quantile(0.25)
            q3 = df.quantile(0.75)
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outlier_mask = (df < lower_bound) | (df > upper_bound)
        else:  # zscore
            z_scores = np.abs((df - df.mean()) / df.std())
            outlier_mask = z_scores > 3

        outlier_indices = df[outlier_mask].index.tolist()
        outlier_values = df[outlier_mask].tolist()

        return outlier_indices, outlier_values

    def compute_correlation(
        self,
        salaries: List[float],
        other_metric: List[float],
    ) -> float:
        """
        Compute Pearson correlation between salary and another metric.

        Args:
            salaries: List of salary values
            other_metric: List of another metric (same length)

        Returns:
            Correlation coefficient
        """
        if self.use_gpu:
            return self._gpu_correlation(salaries, other_metric)
        else:
            return self._cpu_correlation(salaries, other_metric)

    def _gpu_correlation(
        self,
        salaries: List[float],
        other_metric: List[float],
    ) -> float:
        """GPU implementation of correlation."""
        x = cp.array(salaries, dtype=cp.float32)
        y = cp.array(other_metric, dtype=cp.float32)

        correlation = float(cp.corrcoef(x, y)[0, 1])
        return correlation

    def _cpu_correlation(
        self,
        salaries: List[float],
        other_metric: List[float],
    ) -> float:
        """CPU fallback implementation."""
        return float(np.corrcoef(salaries, other_metric)[0, 1])

    def compute_moving_average(
        self,
        salaries: List[float],
        window_size: int = 3,
    ) -> List[float]:
        """
        Compute moving average for time series analysis.

        Args:
            salaries: List of salary values (time-ordered)
            window_size: Window size for moving average

        Returns:
            List of moving average values
        """
        if self.use_gpu:
            return self._gpu_moving_average(salaries, window_size)
        else:
            return self._cpu_moving_average(salaries, window_size)

    def _gpu_moving_average(
        self,
        salaries: List[float],
        window_size: int,
    ) -> List[float]:
        """GPU implementation of moving average."""
        salaries_gpu = cp.array(salaries, dtype=cp.float32)

        # Use cuPy's convolve for efficient moving average
        kernel = cp.ones(window_size) / window_size
        moving_avg = cp.convolve(salaries_gpu, kernel, mode='same')

        return moving_avg.get().tolist()

    def _cpu_moving_average(
        self,
        salaries: List[float],
        window_size: int,
    ) -> List[float]:
        """CPU fallback implementation."""
        import pandas as pd

        df = pd.Series(salaries)
        moving_avg = df.rolling(window=window_size, center=True).mean()

        return moving_avg.fillna(method='bfill').fillna(method='ffill').tolist()

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get GPU performance metrics.

        Returns:
            Dictionary with performance metrics
        """
        if not self.use_gpu:
            return {
                "mode": "CPU",
                "gpu_available": False,
            }

        device = cp.cuda.Device(settings.CUDA_DEVICE)
        mem_info = device.mem_info

        return {
            "mode": "GPU",
            "gpu_available": True,
            "device_id": settings.CUDA_DEVICE,
            "device_name": device.name,
            "total_memory_gb": mem_info[1] / 1e9,
            "free_memory_gb": mem_info[0] / 1e9,
            "used_memory_gb": (mem_info[1] - mem_info[0]) / 1e9,
            "memory_utilization": ((mem_info[1] - mem_info[0]) / mem_info[1]) * 100,
        }


# Global instance
gpu_analytics = GPUAnalytics()
