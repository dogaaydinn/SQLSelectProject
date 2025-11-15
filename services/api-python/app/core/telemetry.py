"""
OpenTelemetry Distributed Tracing
Instrumentation for FastAPI, SQLAlchemy, Redis, and HTTP clients
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

from app.core.config import settings
from app.core.logging import logger


def setup_telemetry(app):
    """
    Configure OpenTelemetry distributed tracing.

    Args:
        app: FastAPI application instance
    """
    if not settings.ENABLE_TRACING:
        logger.info("Distributed tracing disabled")
        return

    # Create resource with service information
    resource = Resource(attributes={
        SERVICE_NAME: settings.APP_NAME,
        SERVICE_VERSION: settings.APP_VERSION,
        "deployment.environment": settings.ENVIRONMENT,
    })

    # Configure tracer provider with sampling
    tracer_provider = TracerProvider(
        resource=resource,
        sampler=TraceIdRatioBased(settings.TRACE_SAMPLE_RATE),
    )

    # Add Jaeger exporter if configured
    if settings.JAEGER_AGENT_HOST:
        jaeger_exporter = JaegerExporter(
            agent_host_name=settings.JAEGER_AGENT_HOST,
            agent_port=settings.JAEGER_AGENT_PORT,
        )
        tracer_provider.add_span_processor(
            BatchSpanProcessor(jaeger_exporter)
        )
        logger.info(
            f"Jaeger exporter configured: {settings.JAEGER_AGENT_HOST}:{settings.JAEGER_AGENT_PORT}"
        )

    # Add console exporter for debugging if in debug mode
    if settings.DEBUG:
        console_exporter = ConsoleSpanExporter()
        tracer_provider.add_span_processor(
            BatchSpanProcessor(console_exporter)
        )

    # Set the global tracer provider
    trace.set_tracer_provider(tracer_provider)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracer_provider,
        excluded_urls="health,metrics",  # Don't trace health checks
    )
    logger.info("FastAPI instrumented with OpenTelemetry")

    # Instrument SQLAlchemy (will auto-detect engines)
    SQLAlchemyInstrumentor().instrument(
        tracer_provider=tracer_provider,
        enable_commenter=True,  # Add trace context to SQL comments
    )
    logger.info("SQLAlchemy instrumented with OpenTelemetry")

    # Instrument Redis
    try:
        RedisInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info("Redis instrumented with OpenTelemetry")
    except Exception as e:
        logger.warning(f"Failed to instrument Redis: {e}")

    # Instrument HTTPX for outgoing requests
    HTTPXClientInstrumentor().instrument(tracer_provider=tracer_provider)
    logger.info("HTTPX client instrumented with OpenTelemetry")

    logger.info(
        f"OpenTelemetry tracing initialized (sample rate: {settings.TRACE_SAMPLE_RATE})"
    )


def get_tracer(name: str = None):
    """
    Get a tracer instance for manual instrumentation.

    Args:
        name: Name for the tracer (defaults to app name)

    Returns:
        Tracer instance
    """
    tracer_name = name or settings.APP_NAME
    return trace.get_tracer(tracer_name)


def add_span_attributes(span, **attributes):
    """
    Add custom attributes to the current span.

    Args:
        span: Span instance
        **attributes: Key-value pairs to add as attributes
    """
    if span and span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


def record_exception(span, exception: Exception):
    """
    Record an exception in the current span.

    Args:
        span: Span instance
        exception: Exception to record
    """
    if span and span.is_recording():
        span.record_exception(exception)
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))
