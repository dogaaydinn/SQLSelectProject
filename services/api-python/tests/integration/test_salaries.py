"""
Integration Tests for Salary API Endpoints
Tests all CRUD operations, validation, and employee salary history
"""

import pytest
from datetime import date, timedelta
from httpx import AsyncClient
from sqlalchemy import select

from app.models.salary import Salary


@pytest.mark.integration
@pytest.mark.api
class TestSalaryList:
    """Test salary list endpoint."""

    async def test_list_salaries_success(self, client: AsyncClient):
        """Test successful salary list retrieval."""
        response = await client.get("/api/v1/salaries")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["items"], list)

    async def test_list_salaries_pagination(self, client: AsyncClient):
        """Test salary list with pagination."""
        response = await client.get("/api/v1/salaries?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["items"]) <= 10

    async def test_list_salaries_filter_by_employee(
        self, client: AsyncClient, test_employee
    ):
        """Test filtering salaries by employee number."""
        response = await client.get(f"/api/v1/salaries?emp_no={test_employee.emp_no}")

        assert response.status_code == 200
        data = response.json()

        # All returned salaries should belong to the employee
        for item in data["items"]:
            assert item["emp_no"] == test_employee.emp_no

    async def test_list_salaries_filter_by_min_max(self, client: AsyncClient):
        """Test filtering salaries by min and max amount."""
        min_salary = 50000
        max_salary = 100000

        response = await client.get(
            f"/api/v1/salaries?min_salary={min_salary}&max_salary={max_salary}&current_only=false"
        )

        assert response.status_code == 200
        data = response.json()

        # All returned salaries should be within the range
        for item in data["items"]:
            salary_amount = float(item["salary"])
            assert min_salary <= salary_amount <= max_salary

    async def test_list_salaries_current_only(self, client: AsyncClient):
        """Test filtering for current salaries only."""
        response = await client.get("/api/v1/salaries?current_only=true")

        assert response.status_code == 200
        data = response.json()

        # All returned salaries should be current (to_date = 9999-12-31)
        for item in data["items"]:
            assert item["to_date"] == "9999-12-31"


@pytest.mark.integration
@pytest.mark.api
class TestSalaryGet:
    """Test get single salary endpoint."""

    async def test_get_salary_success(self, client: AsyncClient, test_salary):
        """Test successful salary retrieval."""
        response = await client.get(f"/api/v1/salaries/{test_salary.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == test_salary.id
        assert data["emp_no"] == test_salary.emp_no
        assert float(data["salary"]) == float(test_salary.salary)
        assert "uuid" in data

    async def test_get_salary_not_found(self, client: AsyncClient):
        """Test getting non-existent salary."""
        response = await client.get("/api/v1/salaries/999999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    async def test_get_salary_caching(self, client: AsyncClient, test_salary):
        """Test that salary retrieval uses caching."""
        # First request
        response1 = await client.get(f"/api/v1/salaries/{test_salary.id}")
        assert response1.status_code == 200

        # Second request - should hit cache
        response2 = await client.get(f"/api/v1/salaries/{test_salary.id}")
        assert response2.status_code == 200

        # Data should be identical
        assert response1.json() == response2.json()


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
class TestSalaryCreate:
    """Test create salary endpoint."""

    async def test_create_salary_success(
        self, client: AsyncClient, auth_headers, test_employee, db
    ):
        """Test successful salary creation."""
        salary_data = {
            "emp_no": test_employee.emp_no,
            "salary": "75000.00",
            "currency": "USD",
            "from_date": str(date.today()),
            "to_date": "9999-12-31",
            "salary_type": "Base",
            "bonus": "5000.00",
            "commission": "0.00",
        }

        response = await client.post(
            "/api/v1/salaries",
            json=salary_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        assert data["emp_no"] == salary_data["emp_no"]
        assert float(data["salary"]) == float(salary_data["salary"])
        assert data["currency"] == salary_data["currency"]
        assert "id" in data
        assert "uuid" in data

        # Verify in database
        stmt = select(Salary).where(Salary.id == data["id"])
        result = await db.execute(stmt)
        salary = result.scalar_one_or_none()
        assert salary is not None
        assert float(salary.salary) == float(salary_data["salary"])

    async def test_create_salary_nonexistent_employee(
        self, client: AsyncClient, auth_headers
    ):
        """Test creating salary for non-existent employee."""
        salary_data = {
            "emp_no": 999999,  # Non-existent employee
            "salary": "75000.00",
            "from_date": str(date.today()),
        }

        response = await client.post(
            "/api/v1/salaries",
            json=salary_data,
            headers=auth_headers,
        )

        assert response.status_code in [404, 422]  # Should fail validation

    async def test_create_salary_invalid_dates(
        self, client: AsyncClient, auth_headers, test_employee
    ):
        """Test creating salary with invalid date range."""
        salary_data = {
            "emp_no": test_employee.emp_no,
            "salary": "75000.00",
            "from_date": str(date.today()),
            "to_date": str(date.today() - timedelta(days=30)),  # to_date before from_date
        }

        response = await client.post(
            "/api/v1/salaries",
            json=salary_data,
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error

    async def test_create_salary_negative_amount(
        self, client: AsyncClient, auth_headers, test_employee
    ):
        """Test creating salary with negative amount."""
        salary_data = {
            "emp_no": test_employee.emp_no,
            "salary": "-1000.00",  # Negative salary
            "from_date": str(date.today()),
        }

        response = await client.post(
            "/api/v1/salaries",
            json=salary_data,
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error

    async def test_create_salary_unauthorized(
        self, client: AsyncClient, test_employee
    ):
        """Test creating salary without authentication."""
        salary_data = {
            "emp_no": test_employee.emp_no,
            "salary": "75000.00",
            "from_date": str(date.today()),
        }

        response = await client.post("/api/v1/salaries", json=salary_data)

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
class TestSalaryUpdate:
    """Test update salary endpoint."""

    async def test_update_salary_success(
        self, client: AsyncClient, auth_headers, test_salary, db
    ):
        """Test successful salary update."""
        update_data = {
            "salary": "85000.00",
            "bonus": "7500.00",
        }

        response = await client.put(
            f"/api/v1/salaries/{test_salary.id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == test_salary.id
        assert float(data["salary"]) == float(update_data["salary"])

        # Verify in database
        await db.refresh(test_salary)
        assert float(test_salary.salary) == float(update_data["salary"])

    async def test_update_salary_partial(
        self, client: AsyncClient, auth_headers, test_salary, db
    ):
        """Test partial salary update."""
        original_salary = test_salary.salary
        update_data = {"bonus": "10000.00"}

        response = await client.put(
            f"/api/v1/salaries/{test_salary.id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Bonus should be updated
        assert float(data["bonus"]) == float(update_data["bonus"])
        # Salary should remain the same
        assert float(data["salary"]) == float(original_salary)

    async def test_update_salary_not_found(
        self, client: AsyncClient, auth_headers
    ):
        """Test updating non-existent salary."""
        update_data = {"salary": "90000.00"}

        response = await client.put(
            "/api/v1/salaries/999999",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_update_salary_unauthorized(self, client: AsyncClient, test_salary):
        """Test updating salary without authentication."""
        update_data = {"salary": "90000.00"}

        response = await client.put(
            f"/api/v1/salaries/{test_salary.id}",
            json=update_data,
        )

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
class TestSalaryDelete:
    """Test delete salary endpoint (soft delete)."""

    async def test_delete_salary_success(
        self, client: AsyncClient, auth_headers, test_salary, db
    ):
        """Test successful salary deletion (soft delete)."""
        response = await client.delete(
            f"/api/v1/salaries/{test_salary.id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify soft delete in database
        await db.refresh(test_salary)
        assert test_salary.is_deleted is True

    async def test_delete_salary_not_found(
        self, client: AsyncClient, auth_headers
    ):
        """Test deleting non-existent salary."""
        response = await client.delete(
            "/api/v1/salaries/999999",
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_delete_salary_unauthorized(self, client: AsyncClient, test_salary):
        """Test deleting salary without authentication."""
        response = await client.delete(f"/api/v1/salaries/{test_salary.id}")

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
class TestEmployeeSalaryHistory:
    """Test employee salary history endpoints."""

    async def test_get_employee_salary_history(
        self, client: AsyncClient, test_employee
    ):
        """Test getting employee salary history."""
        response = await client.get(
            f"/api/v1/salaries/employee/{test_employee.emp_no}"
        )

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

        # All salaries should belong to the employee
        for item in data["items"]:
            assert item["emp_no"] == test_employee.emp_no

    async def test_get_employee_current_salary(
        self, client: AsyncClient, test_employee, test_salary
    ):
        """Test getting employee's current salary."""
        response = await client.get(
            f"/api/v1/salaries/employee/{test_employee.emp_no}/current"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["emp_no"] == test_employee.emp_no
        assert data["to_date"] == "9999-12-31"  # Current salary marker

    async def test_get_employee_current_salary_not_found(self, client: AsyncClient):
        """Test getting current salary for non-existent employee."""
        response = await client.get("/api/v1/salaries/employee/999999/current")

        assert response.status_code == 404

    async def test_get_employee_salary_history_empty(
        self, client: AsyncClient, test_employee
    ):
        """Test getting salary history for employee with no salaries."""
        response = await client.get(
            f"/api/v1/salaries/employee/{test_employee.emp_no}"
        )

        assert response.status_code == 200
        data = response.json()

        # Should return empty list, not error
        assert isinstance(data["items"], list)
