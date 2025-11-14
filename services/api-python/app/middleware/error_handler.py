"""
Error Handler Middleware
Centralized error handling and logging
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.core.logging import logger


async def error_handler_middleware(request: Request, call_next):
    """Handle errors and exceptions."""
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        request_id = getattr(request.state, "request_id", None)

        logger.exception(
            "Unhandled exception in request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "request_id": request_id,
                "exception": str(exc),
            },
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "request_id": request_id,
            },
        )
