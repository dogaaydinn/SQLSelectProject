"""
Timing Middleware
Measures and logs request processing time
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.logging import logger


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to measure request processing time."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Measure request processing time."""
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time
        process_time_ms = round(process_time * 1000, 2)

        # Add to response headers
        response.headers["X-Response-Time"] = f"{process_time_ms}ms"

        # Log slow requests
        if process_time_ms > 1000:  # > 1 second
            logger.warning(
                f"Slow request detected",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "response_time_ms": process_time_ms,
                    "status_code": response.status_code,
                    "request_id": getattr(request.state, "request_id", None),
                },
            )

        return response
