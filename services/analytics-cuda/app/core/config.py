"""
CUDA Analytics Service Configuration
Environment-based configuration for GPU-accelerated analytics
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    APP_NAME: str = "CUDA Analytics Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    WORKERS: int = 4

    # Database (read-only connection to main DB)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@db:5432/employees_db"
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Redis Cache
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    CACHE_TTL: int = 300  # 5 minutes default

    # CUDA/GPU Configuration
    CUDA_DEVICE: int = 0  # Default GPU device
    USE_GPU: bool = True  # Set to False to force CPU fallback
    GPU_MEMORY_FRACTION: float = 0.8  # Use 80% of GPU memory

    # cuDF Configuration
    CUDF_SPILL: bool = True  # Enable spilling to host memory
    CUDF_SPILL_DEVICE_LIMIT: str = "8GB"

    # Performance
    BATCH_SIZE: int = 10000  # Batch size for GPU operations
    MAX_WORKERS: int = 4  # For CPU fallback parallelization

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090

    # Security
    API_KEY_HEADER: str = "X-API-Key"
    ALLOWED_ORIGINS: list = ["*"]  # Configure for production

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
