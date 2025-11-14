"""
Integration Tests for Analytics API Endpoints
Tests statistical analysis, aggregations, and reporting endpoints
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.slow
class TestSalaryStatistics:
    """Test salary statistics endpoint."""

    async def test_get_salary_statistics_success(self, client: AsyncClient):
        """Test successful salary statistics retrieval."""
        response = await client.get("/api/v1/analytics/salary-statistics")

        assert response.status_code == 200
        data = response.json()

        assert "total_employees" in data
        assert "avg_salary" in data
        assert "min_salary" in data
        assert "max_salary" in data
        assert "median_salary" in data
        assert "total_payroll" in data
        assert "std_deviation" in data

        # Total employees should be a positive integer
        assert isinstance(data["total_employees"], int)
        assert data["total_employees"] >= 0

    async def test_get_salary_statistics_by_department(
        self, client: AsyncClient, test_department
    ):
        """Test salary statistics filtered by department."""
        response = await client.get(
            f"/api/v1/analytics/salary-statistics?dept_no={test_department.dept_no}"
        )

        assert response.status_code == 200
        data = response.json()

        assert "total_employees" in data
        assert "avg_salary" in data

    async def test_get_salary_statistics_current_only(self, client: AsyncClient):
        """Test salary statistics for current salaries only."""
        response = await client.get(
            "/api/v1/analytics/salary-statistics?current_only=true"
        )

        assert response.status_code == 200
        data = response.json()

        assert "total_employees" in data

    async def test_get_salary_statistics_all_time(self, client: AsyncClient):
        """Test salary statistics for all time (historical)."""
        response = await client.get(
            "/api/v1/analytics/salary-statistics?current_only=false"
        )

        assert response.status_code == 200
        data = response.json()

        assert "total_employees" in data

    async def test_get_salary_statistics_caching(self, client: AsyncClient):
        """Test that salary statistics uses caching."""
        # First request
        response1 = await client.get("/api/v1/analytics/salary-statistics")
        assert response1.status_code == 200

        # Second request - should hit cache
        response2 = await client.get("/api/v1/analytics/salary-statistics")
        assert response2.status_code == 200

        # Data should be identical
        assert response1.json() == response2.json()


@pytest.mark.integration
@pytest.mark.api
class TestSalaryDistribution:
    """Test salary distribution endpoint."""

    async def test_get_salary_distribution_success(self, client: AsyncClient):
        """Test successful salary distribution retrieval."""
        response = await client.get("/api/v1/analytics/salary-distribution")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        # Each item should have required fields
        for item in data:
            assert "salary_range" in item
            assert "count" in item
            assert "percentage" in item
            assert isinstance(item["count"], int)
            assert isinstance(item["percentage"], (int, float))

    async def test_get_salary_distribution_percentages(self, client: AsyncClient):
        """Test that salary distribution percentages sum to ~100%."""
        response = await client.get("/api/v1/analytics/salary-distribution")

        assert response.status_code == 200
        data = response.json()

        # Sum of all percentages should be close to 100%
        total_percentage = sum(item["percentage"] for item in data)
        assert 99.0 <= total_percentage <= 101.0  # Allow small rounding errors


@pytest.mark.integration
@pytest.mark.api
class TestDepartmentPerformance:
    """Test department performance endpoint."""

    async def test_get_department_performance_success(self, client: AsyncClient):
        """Test successful department performance retrieval."""
        response = await client.get("/api/v1/analytics/department-performance")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        # Each department should have required fields
        for item in data:
            assert "dept_no" in item
            assert "dept_name" in item
            assert "employee_count" in item
            assert isinstance(item["employee_count"], int)

    async def test_get_department_performance_specific(
        self, client: AsyncClient, test_department
    ):
        """Test department performance for specific department."""
        response = await client.get(
            f"/api/v1/analytics/department-performance?dept_no={test_department.dept_no}"
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        # Should include the requested department
        dept_nos = [item["dept_no"] for item in data]
        assert test_department.dept_no in dept_nos

    async def test_get_department_performance_metrics(self, client: AsyncClient):
        """Test that department performance includes all metrics."""
        response = await client.get("/api/v1/analytics/department-performance")

        assert response.status_code == 200
        data = response.json()

        if data:  # If there's data
            item = data[0]
            assert "avg_salary" in item
            assert "total_payroll" in item
            assert "budget" in item
            assert "budget_utilization" in item
            assert "avg_tenure_days" in item


@pytest.mark.integration
@pytest.mark.api
class TestEmployeeTrends:
    """Test employee trends endpoint."""

    async def test_get_employee_trends_success(self, client: AsyncClient):
        """Test successful employee trends retrieval."""
        response = await client.get("/api/v1/analytics/employee-trends")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        # Each period should have required fields
        for item in data:
            assert "period" in item
            assert "new_hires" in item
            assert "terminations" in item
            assert "net_change" in item
            assert "total_employees" in item

    async def test_get_employee_trends_by_year(self, client: AsyncClient):
        """Test employee trends grouped by year."""
        response = await client.get(
            "/api/v1/analytics/employee-trends?period=year"
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

    async def test_get_employee_trends_by_quarter(self, client: AsyncClient):
        """Test employee trends grouped by quarter."""
        response = await client.get(
            "/api/v1/analytics/employee-trends?period=quarter"
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

    async def test_get_employee_trends_by_month(self, client: AsyncClient):
        """Test employee trends grouped by month."""
        response = await client.get(
            "/api/v1/analytics/employee-trends?period=month"
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)


@pytest.mark.integration
@pytest.mark.api
class TestGenderDiversity:
    """Test gender diversity endpoint."""

    async def test_get_gender_diversity_success(self, client: AsyncClient):
        """Test successful gender diversity retrieval."""
        response = await client.get("/api/v1/analytics/gender-diversity")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        # Each gender should have required fields
        for item in data:
            assert "gender" in item
            assert "count" in item
            assert "percentage" in item
            assert "avg_salary" in item
            assert isinstance(item["count"], int)
            assert isinstance(item["percentage"], (int, float))

    async def test_get_gender_diversity_percentages(self, client: AsyncClient):
        """Test that gender diversity percentages sum to ~100%."""
        response = await client.get("/api/v1/analytics/gender-diversity")

        assert response.status_code == 200
        data = response.json()

        # Sum of all percentages should be close to 100%
        total_percentage = sum(item["percentage"] for item in data)
        assert 99.0 <= total_percentage <= 101.0

    async def test_get_gender_diversity_by_department(
        self, client: AsyncClient, test_department
    ):
        """Test gender diversity filtered by department."""
        response = await client.get(
            f"/api/v1/analytics/gender-diversity?dept_no={test_department.dept_no}"
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)


@pytest.mark.integration
@pytest.mark.api
class TestTitleDistribution:
    """Test title distribution endpoint."""

    async def test_get_title_distribution_success(self, client: AsyncClient):
        """Test successful title distribution retrieval."""
        response = await client.get("/api/v1/analytics/title-distribution")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        # Each title should have required fields
        for item in data:
            assert "title" in item
            assert "count" in item
            assert "percentage" in item
            assert "avg_salary" in item
            assert isinstance(item["count"], int)
            assert isinstance(item["percentage"], (int, float))

    async def test_get_title_distribution_percentages(self, client: AsyncClient):
        """Test that title distribution percentages sum to ~100%."""
        response = await client.get("/api/v1/analytics/title-distribution")

        assert response.status_code == 200
        data = response.json()

        # Sum of all percentages should be close to 100%
        total_percentage = sum(item["percentage"] for item in data)
        assert 99.0 <= total_percentage <= 101.0

    async def test_get_title_distribution_by_department(
        self, client: AsyncClient, test_department
    ):
        """Test title distribution filtered by department."""
        response = await client.get(
            f"/api/v1/analytics/title-distribution?dept_no={test_department.dept_no}"
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)


@pytest.mark.integration
@pytest.mark.api
class TestAnalyticsSummary:
    """Test analytics summary endpoint."""

    async def test_get_summary_success(self, client: AsyncClient):
        """Test successful analytics summary retrieval."""
        response = await client.get("/api/v1/analytics/summary")

        assert response.status_code == 200
        data = response.json()

        # Check for expected summary fields
        assert "total_employees" in data
        assert "total_departments" in data
        assert isinstance(data["total_employees"], int)
        assert isinstance(data["total_departments"], int)

    async def test_get_summary_caching(self, client: AsyncClient):
        """Test that analytics summary uses caching."""
        # First request
        response1 = await client.get("/api/v1/analytics/summary")
        assert response1.status_code == 200

        # Second request - should hit cache
        response2 = await client.get("/api/v1/analytics/summary")
        assert response2.status_code == 200

        # Data should be identical
        assert response1.json() == response2.json()


@pytest.mark.integration
@pytest.mark.api
class TestAnalyticsPerformance:
    """Test analytics endpoint performance."""

    @pytest.mark.slow
    async def test_analytics_endpoints_response_time(self, client: AsyncClient):
        """Test that analytics endpoints respond within reasonable time."""
        import time

        endpoints = [
            "/api/v1/analytics/salary-statistics",
            "/api/v1/analytics/salary-distribution",
            "/api/v1/analytics/department-performance",
            "/api/v1/analytics/gender-diversity",
            "/api/v1/analytics/title-distribution",
        ]

        for endpoint in endpoints:
            start = time.time()
            response = await client.get(endpoint)
            elapsed = time.time() - start

            assert response.status_code == 200
            # Should respond within 2 seconds (first call without cache)
            assert elapsed < 2.0, f"{endpoint} took {elapsed:.2f}s"

    @pytest.mark.slow
    async def test_analytics_caching_improves_performance(self, client: AsyncClient):
        """Test that caching improves analytics performance."""
        import time

        endpoint = "/api/v1/analytics/salary-statistics"

        # First call - cache miss
        start1 = time.time()
        response1 = await client.get(endpoint)
        elapsed1 = time.time() - start1
        assert response1.status_code == 200

        # Second call - cache hit
        start2 = time.time()
        response2 = await client.get(endpoint)
        elapsed2 = time.time() - start2
        assert response2.status_code == 200

        # Cached response should be faster
        # (allowing for variance but should be noticeably faster)
        assert elapsed2 < elapsed1 or elapsed2 < 0.1
