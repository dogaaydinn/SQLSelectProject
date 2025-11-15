"""
OpenTelemetry Distributed Tracing for CUDA Analytics Service
Instrumentation for FastAPI and database queries
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

from app.core.config import settings
from app.core.logging import logger


def setup_telemetry(app):
    """
    Configure OpenTelemetry distributed tracing for analytics service.

    Args:
        app: FastAPI application instance
    """
    if not settings.ENABLE_METRICS:  # Using same flag as metrics
        logger.info("Distributed tracing disabled")
        return

    # Create resource with service information
    resource = Resource(attributes={
        SERVICE_NAME: settings.APP_NAME,
        SERVICE_VERSION: settings.APP_VERSION,
        "service.type": "analytics",
        "gpu.enabled": settings.USE_GPU,
    })

    # Configure tracer provider
    tracer_provider = TracerProvider(
        resource=resource,
        sampler=TraceIdRatioBased(1.0),  # Sample all traces for analytics
    )

    # Add Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger",  # Docker service name
        agent_port=6831,
    )
    tracer_provider.add_span_processor(
        BatchSpanProcessor(jaeger_exporter)
    )

    # Set the global tracer provider
    trace.set_tracer_provider(tracer_provider)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracer_provider,
        excluded_urls="health,metrics",
    )

    # Instrument SQLAlchemy
    SQLAlchemyInstrumentor().instrument(
        tracer_provider=tracer_provider,
        enable_commenter=True,
    )

    logger.info("OpenTelemetry tracing initialized for CUDA analytics service")


def get_tracer(name: str = None):
    """Get a tracer instance for manual instrumentation."""
    tracer_name = name or settings.APP_NAME
    return trace.get_tracer(tracer_name)
