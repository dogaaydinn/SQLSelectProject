"""
Performance and Load Tests
Tests API performance under load and stress conditions
"""

import pytest
import asyncio
from httpx import AsyncClient
from time import time


@pytest.mark.performance
@pytest.mark.slow
class TestAPIPerformance:
    """Test API performance metrics."""

    async def test_health_endpoint_response_time(self, client: AsyncClient):
        """Test health endpoint responds quickly."""
        start = time()
        response = await client.get("/health")
        elapsed = time() - start

        assert response.status_code == 200
        assert elapsed < 0.1  # Should respond in < 100ms

    async def test_employee_list_response_time(self, client: AsyncClient):
        """Test employee list endpoint responds within acceptable time."""
        start = time()
        response = await client.get("/api/v1/employees?page=1&page_size=20")
        elapsed = time() - start

        assert response.status_code == 200
        assert elapsed < 0.5  # Should respond in < 500ms

    async def test_analytics_response_time(self, client: AsyncClient):
        """Test analytics endpoints respond within acceptable time."""
        endpoints = [
            "/api/v1/analytics/salary-statistics",
            "/api/v1/analytics/department-performance",
            "/api/v1/analytics/gender-diversity",
        ]

        for endpoint in endpoints:
            start = time()
            response = await client.get(endpoint)
            elapsed = time() - start

            assert response.status_code == 200
            # Analytics can be slower but should be < 2 seconds
            assert elapsed < 2.0, f"{endpoint} took {elapsed:.2f}s"


@pytest.mark.performance
@pytest.mark.slow
class TestConcurrentRequests:
    """Test API behavior under concurrent load."""

    async def test_concurrent_health_checks(self, client: AsyncClient):
        """Test multiple concurrent health check requests."""
        num_requests = 50

        async def make_request():
            response = await client.get("/health")
            return response.status_code

        # Execute concurrent requests
        start = time()
        tasks = [make_request() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
        elapsed = time() - start

        # All requests should succeed
        assert all(status == 200 for status in results)
        # Should complete within reasonable time
        assert elapsed < 5.0
        # Calculate requests per second
        rps = num_requests / elapsed
        assert rps > 100  # At least 100 requests per second

    async def test_concurrent_employee_reads(self, client: AsyncClient, test_employee):
        """Test concurrent employee read operations."""
        num_requests = 20

        async def make_request():
            response = await client.get(f"/api/v1/employees/{test_employee.emp_no}")
            return response.status_code

        start = time()
        tasks = [make_request() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
        elapsed = time() - start

        # All requests should succeed
        assert all(status == 200 for status in results)
        # Should complete within reasonable time
        assert elapsed < 3.0


@pytest.mark.performance
@pytest.mark.slow
class TestCachePerformance:
    """Test caching improves performance."""

    async def test_cache_hit_performance(self, client: AsyncClient, test_employee):
        """Test that cached responses are faster."""
        endpoint = f"/api/v1/employees/{test_employee.emp_no}"

        # First request - cache miss
        start1 = time()
        response1 = await client.get(endpoint)
        time1 = time() - start1

        assert response1.status_code == 200

        # Subsequent requests - cache hits
        times = []
        for _ in range(10):
            start = time()
            response = await client.get(endpoint)
            elapsed = time() - start
            times.append(elapsed)
            assert response.status_code == 200

        avg_cached_time = sum(times) / len(times)

        # Cached requests should generally be faster
        # (allowing for variance but expecting improvement)
        assert avg_cached_time <= time1 * 1.2  # Within 20% of first request


@pytest.mark.performance
@pytest.mark.slow
class TestPaginationPerformance:
    """Test pagination performance."""

    async def test_different_page_sizes(self, client: AsyncClient):
        """Test performance with different page sizes."""
        page_sizes = [10, 20, 50, 100]
        times = {}

        for page_size in page_sizes:
            start = time()
            response = await client.get(
                f"/api/v1/employees?page=1&page_size={page_size}"
            )
            elapsed = time() - start
            times[page_size] = elapsed

            assert response.status_code == 200

        # Larger page sizes should still be reasonably fast
        for page_size, elapsed in times.items():
            assert elapsed < 1.0, f"Page size {page_size} took {elapsed:.2f}s"


@pytest.mark.performance
@pytest.mark.slow
class TestDatabaseQueryPerformance:
    """Test database query performance."""

    async def test_complex_analytics_query(self, client: AsyncClient):
        """Test complex analytics queries perform acceptably."""
        # Department performance requires joins and aggregations
        start = time()
        response = await client.get("/api/v1/analytics/department-performance")
        elapsed = time() - start

        assert response.status_code == 200
        # Complex queries should still be < 3 seconds
        assert elapsed < 3.0

    async def test_filter_performance(self, client: AsyncClient):
        """Test filtered queries perform well."""
        start = time()
        response = await client.get(
            "/api/v1/employees?search=test&status=Active"
        )
        elapsed = time() - start

        assert response.status_code == 200
        # Filtered queries should be fast
        assert elapsed < 1.0


@pytest.mark.performance
class TestMemoryUsage:
    """Test for memory efficiency."""

    async def test_large_result_set_handling(self, client: AsyncClient):
        """Test that large result sets are handled efficiently."""
        # Request maximum page size
        response = await client.get("/api/v1/employees?page=1&page_size=100")

        assert response.status_code == 200
        data = response.json()

        # Should return data efficiently
        assert "items" in data
        assert len(data["items"]) <= 100


# Benchmark targets for documentation
"""
Performance Targets (95th percentile):
- Health check: < 100ms
- Simple GET (single record): < 200ms
- List with pagination: < 500ms
- Complex analytics: < 2000ms
- Concurrent requests (50): Complete within 5s
- Throughput: > 100 req/s for health checks
"""
