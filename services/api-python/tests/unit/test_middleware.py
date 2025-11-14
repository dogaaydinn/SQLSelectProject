"""
Unit Tests for Middleware
Tests custom middleware for request handling, timing, and error handling
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.middleware.base import RequestResponseEndpoint

from app.middleware.request_id import RequestIDMiddleware
from app.middleware.timing import TimingMiddleware
from app.middleware.error_handler import error_handler_middleware


@pytest.mark.unit
class TestRequestIDMiddleware:
    """Test RequestID middleware."""

    @pytest.fixture
    def middleware(self):
        """Create RequestID middleware instance."""
        app = MagicMock()
        return RequestIDMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.state = MagicMock()
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create a mock call_next function."""
        async def call_next(request):
            response = Response(content=b"test", status_code=200)
            response.headers = {}
            return response
        return call_next

    async def test_request_id_generation(self, middleware, mock_request, mock_call_next):
        """Test that request ID is generated if not provided."""
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should have generated a request ID
        assert hasattr(mock_request.state, 'request_id')
        assert isinstance(uuid.UUID(mock_request.state.request_id), uuid.UUID)

    async def test_request_id_from_header(self, middleware, mock_request, mock_call_next):
        """Test that request ID is taken from header if provided."""
        test_request_id = str(uuid.uuid4())
        mock_request.headers = {"X-Request-ID": test_request_id}

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should use provided request ID
        assert mock_request.state.request_id == test_request_id

    async def test_request_id_in_response_headers(self, middleware, mock_request, mock_call_next):
        """Test that request ID is added to response headers."""
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Response should have request ID header
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] == mock_request.state.request_id


@pytest.mark.unit
class TestTimingMiddleware:
    """Test Timing middleware."""

    @pytest.fixture
    def middleware(self):
        """Create Timing middleware instance."""
        app = MagicMock()
        return TimingMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = MagicMock(spec=Request)
        request.url = MagicMock()
        request.url.path = "/api/v1/test"
        request.method = "GET"
        request.state = MagicMock()
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create a mock call_next function."""
        async def call_next(request):
            import asyncio
            await asyncio.sleep(0.01)  # Simulate processing time
            response = Response(content=b"test", status_code=200)
            response.headers = {}
            return response
        return call_next

    async def test_response_time_header(self, middleware, mock_request, mock_call_next):
        """Test that response time header is added."""
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Response should have timing header
        assert "X-Response-Time" in response.headers
        response_time = response.headers["X-Response-Time"]
        assert response_time.endswith("ms")

    async def test_response_time_measurement(self, middleware, mock_request, mock_call_next):
        """Test that response time is measured correctly."""
        response = await middleware.dispatch(mock_request, mock_call_next)

        response_time_str = response.headers["X-Response-Time"]
        response_time = float(response_time_str.replace("ms", ""))

        # Should have measured some time (at least 10ms from sleep)
        assert response_time >= 10.0

    async def test_timing_for_different_endpoints(self, middleware, mock_request, mock_call_next):
        """Test timing works for different endpoints."""
        test_paths = ["/api/v1/employees", "/api/v1/departments", "/health"]

        for path in test_paths:
            mock_request.url.path = path
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert "X-Response-Time" in response.headers


@pytest.mark.unit
class TestErrorHandlerMiddleware:
    """Test error handler middleware."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = MagicMock(spec=Request)
        request.url = MagicMock()
        request.url.path = "/api/v1/test"
        request.method = "GET"
        request.state = MagicMock()
        request.state.request_id = str(uuid.uuid4())
        return request

    async def test_successful_request(self, mock_request):
        """Test middleware passes through successful requests."""
        async def call_next(request):
            return Response(content=b"success", status_code=200)

        response = await error_handler_middleware(mock_request, call_next)

        assert response.status_code == 200
        assert response.body == b"success"

    async def test_error_handling(self, mock_request):
        """Test middleware catches and handles errors."""
        async def call_next(request):
            raise ValueError("Test error")

        response = await error_handler_middleware(mock_request, call_next)

        # Should return error response
        assert response.status_code == 500
        assert isinstance(response, JSONResponse)

    async def test_error_response_structure(self, mock_request):
        """Test error response has correct structure."""
        async def call_next(request):
            raise RuntimeError("Test error message")

        response = await error_handler_middleware(mock_request, call_next)

        # Parse JSON response
        import json
        body = json.loads(response.body)

        assert "error" in body
        assert "message" in body
        assert "request_id" in body
        assert body["request_id"] == mock_request.state.request_id

    async def test_different_error_types(self, mock_request):
        """Test middleware handles different error types."""
        error_types = [
            ValueError("Value error"),
            KeyError("Key error"),
            RuntimeError("Runtime error"),
            Exception("Generic error"),
        ]

        for error in error_types:
            async def call_next(request):
                raise error

            response = await error_handler_middleware(mock_request, call_next)
            assert response.status_code == 500


@pytest.mark.unit
class TestMiddlewareIntegration:
    """Test middleware integration."""

    async def test_middleware_chain(self):
        """Test that multiple middleware work together."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        # Add middleware
        from app.middleware.request_id import RequestIDMiddleware
        from app.middleware.timing import TimingMiddleware

        app.add_middleware(TimingMiddleware)
        app.add_middleware(RequestIDMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        # Both middleware should have added headers
        assert "X-Request-ID" in response.headers
        assert "X-Response-Time" in response.headers
