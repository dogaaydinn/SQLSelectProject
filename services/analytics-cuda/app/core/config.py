"""
Analytics Service Configuration
Manages GPU/CPU selection and performance settings
"""

from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Analytics service settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    SERVICE_NAME: str = "Analytics CUDA Service"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    WORKERS: int = 1

    # Processing Mode
    PROCESSING_MODE: Literal["auto", "gpu", "cpu"] = "auto"
    GPU_DEVICE_ID: int = 0
    CPU_WORKERS: int = 4  # Number of CPU workers for parallel processing

    # Database (shared with main API)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "employees"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    # Performance
    BATCH_SIZE: int = 10000  # Records per batch for processing
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 600  # 10 minutes

    # GPU Settings
    GPU_MEMORY_FRACTION: float = 0.8  # Use 80% of GPU memory
    ENABLE_CUDA: bool = False  # Set to True if CUDA is available
    CUDA_VISIBLE_DEVICES: str = "0"

    # Benchmarking
    ENABLE_PROFILING: bool = True
    BENCHMARK_ITERATIONS: int = 10

    @property
    def database_url(self) -> str:
        """Construct database URL."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def should_use_gpu(self) -> bool:
        """Determine if GPU should be used."""
        if self.PROCESSING_MODE == "cpu":
            return False
        if self.PROCESSING_MODE == "gpu":
            return self.ENABLE_CUDA
        # Auto mode
        return self.ENABLE_CUDA and self._cuda_available()

    def _cuda_available(self) -> bool:
        """Check if CUDA is available."""
        try:
            import cupy as cp
            return cp.cuda.is_available()
        except (ImportError, Exception):
            return False


settings = Settings()
