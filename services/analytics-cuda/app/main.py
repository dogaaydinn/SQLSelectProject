"""
CUDA Analytics Service
GPU-accelerated salary analytics with FastAPI
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.core.logging import logger
from app.core.database import init_db, close_db
from app.core.telemetry import setup_telemetry
from app.api.v1.endpoints import analytics, benchmark


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Initialize database
    await init_db()

    # Log GPU status
    from app.cuda.gpu_analytics import gpu_analytics

    metrics = gpu_analytics.get_performance_metrics()
    logger.info(f"Analytics mode: {metrics['mode']}")
    if metrics['gpu_available']:
        logger.info(
            f"GPU Device: {metrics['device_name']} "
            f"({metrics['total_memory_gb']:.2f} GB)"
        )

    yield

    # Shutdown
    logger.info("Shutting down service")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="GPU-accelerated salary analytics using CUDA, cuPy, and cuDF",
    lifespan=lifespan,
)

# Initialize OpenTelemetry distributed tracing
setup_telemetry(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    analytics.router,
    prefix="/api/v1/analytics",
    tags=["Analytics"],
)
app.include_router(
    benchmark.router,
    prefix="/api/v1/benchmark",
    tags=["Benchmarking"],
)

# Prometheus metrics
if settings.ENABLE_METRICS:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status
    """
    from app.cuda.gpu_analytics import gpu_analytics

    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "gpu_mode": gpu_analytics.use_gpu,
    }


@app.get("/")
async def root():
    """
    Root endpoint with service information.

    Returns:
        Service information
    """
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "GPU-accelerated salary analytics",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics" if settings.ENABLE_METRICS else None,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
    )
