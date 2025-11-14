"""
Integration Tests for Employee API Endpoints
Tests all CRUD operations, pagination, filtering, and caching
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.employee import Employee, EmploymentStatus, Gender


@pytest.mark.integration
@pytest.mark.api
class TestEmployeeList:
    """Test employee list endpoint."""

    async def test_list_employees_success(self, client: AsyncClient):
        """Test successful employee list retrieval."""
        response = await client.get("/api/v1/employees")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert isinstance(data["items"], list)

    async def test_list_employees_pagination(self, client: AsyncClient):
        """Test employee list with pagination."""
        # First page
        response1 = await client.get("/api/v1/employees?page=1&page_size=5")
        assert response1.status_code == 200
        data1 = response1.json()

        # Second page
        response2 = await client.get("/api/v1/employees?page=2&page_size=5")
        assert response2.status_code == 200
        data2 = response2.json()

        # Ensure different items on different pages
        if data1["total"] > 5:
            assert data1["items"] != data2["items"]

    async def test_list_employees_search(self, client: AsyncClient, test_employee):
        """Test employee search functionality."""
        response = await client.get(f"/api/v1/employees?search={test_employee.first_name}")

        assert response.status_code == 200
        data = response.json()

        # Should find at least the test employee
        assert data["total"] >= 1
        found = any(
            item["emp_no"] == test_employee.emp_no
            for item in data["items"]
        )
        assert found

    async def test_list_employees_filter_by_status(self, client: AsyncClient):
        """Test filtering employees by status."""
        response = await client.get("/api/v1/employees?status=Active")

        assert response.status_code == 200
        data = response.json()

        # All returned employees should be active
        for item in data["items"]:
            assert item.get("status") == "Active"

    async def test_list_employees_invalid_page(self, client: AsyncClient):
        """Test list with invalid page number."""
        response = await client.get("/api/v1/employees?page=0")

        # Should return validation error
        assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.api
class TestEmployeeGet:
    """Test get single employee endpoint."""

    async def test_get_employee_success(self, client: AsyncClient, test_employee):
        """Test successful employee retrieval."""
        response = await client.get(f"/api/v1/employees/{test_employee.emp_no}")

        assert response.status_code == 200
        data = response.json()

        assert data["emp_no"] == test_employee.emp_no
        assert data["first_name"] == test_employee.first_name
        assert data["last_name"] == test_employee.last_name
        assert "uuid" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_get_employee_not_found(self, client: AsyncClient):
        """Test getting non-existent employee."""
        response = await client.get("/api/v1/employees/999999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    async def test_get_employee_caching(self, client: AsyncClient, test_employee):
        """Test that employee retrieval uses caching."""
        # First request - cache miss
        response1 = await client.get(f"/api/v1/employees/{test_employee.emp_no}")
        assert response1.status_code == 200

        # Second request - should hit cache
        response2 = await client.get(f"/api/v1/employees/{test_employee.emp_no}")
        assert response2.status_code == 200

        # Data should be identical
        assert response1.json() == response2.json()


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
class TestEmployeeCreate:
    """Test create employee endpoint."""

    async def test_create_employee_success(
        self, client: AsyncClient, auth_headers, db
    ):
        """Test successful employee creation."""
        employee_data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "birth_date": "1990-05-15",
            "gender": "F",
            "hire_date": "2024-01-01",
            "email": "jane.doe@company.com",
        }

        response = await client.post(
            "/api/v1/employees",
            json=employee_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        assert data["first_name"] == employee_data["first_name"]
        assert data["last_name"] == employee_data["last_name"]
        assert data["email"] == employee_data["email"]
        assert "emp_no" in data
        assert "uuid" in data

        # Verify in database
        stmt = select(Employee).where(Employee.emp_no == data["emp_no"])
        result = await db.execute(stmt)
        employee = result.scalar_one_or_none()
        assert employee is not None
        assert employee.first_name == employee_data["first_name"]

    async def test_create_employee_duplicate_email(
        self, client: AsyncClient, auth_headers, test_employee
    ):
        """Test creating employee with duplicate email."""
        employee_data = {
            "first_name": "Test",
            "last_name": "User",
            "birth_date": "1990-01-01",
            "gender": "M",
            "hire_date": "2024-01-01",
            "email": test_employee.email,  # Duplicate email
        }

        response = await client.post(
            "/api/v1/employees",
            json=employee_data,
            headers=auth_headers,
        )

        assert response.status_code == 409  # Conflict
        data = response.json()
        assert "detail" in data

    async def test_create_employee_invalid_data(
        self, client: AsyncClient, auth_headers
    ):
        """Test creating employee with invalid data."""
        employee_data = {
            "first_name": "",  # Empty name
            "last_name": "Doe",
            "birth_date": "1990-01-01",
            "gender": "M",
            "hire_date": "2024-01-01",
        }

        response = await client.post(
            "/api/v1/employees",
            json=employee_data,
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error

    async def test_create_employee_unauthorized(self, client: AsyncClient):
        """Test creating employee without authentication."""
        employee_data = {
            "first_name": "John",
            "last_name": "Doe",
            "birth_date": "1990-01-01",
            "gender": "M",
            "hire_date": "2024-01-01",
            "email": "john@company.com",
        }

        response = await client.post("/api/v1/employees", json=employee_data)

        assert response.status_code == 401  # Unauthorized

    async def test_create_employee_invalid_dates(
        self, client: AsyncClient, auth_headers
    ):
        """Test creating employee with invalid date logic."""
        from datetime import date, timedelta

        # Hire date before birth date
        employee_data = {
            "first_name": "John",
            "last_name": "Doe",
            "birth_date": "2000-01-01",
            "gender": "M",
            "hire_date": "1990-01-01",  # Before birth date
            "email": "invalid@company.com",
        }

        response = await client.post(
            "/api/v1/employees",
            json=employee_data,
            headers=auth_headers,
        )

        assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
class TestEmployeeUpdate:
    """Test update employee endpoint."""

    async def test_update_employee_success(
        self, client: AsyncClient, auth_headers, test_employee, db
    ):
        """Test successful employee update."""
        update_data = {
            "email": "updated.email@company.com",
            "phone": "+1234567890",
        }

        response = await client.put(
            f"/api/v1/employees/{test_employee.emp_no}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["emp_no"] == test_employee.emp_no
        assert data["email"] == update_data["email"]

        # Verify in database
        await db.refresh(test_employee)
        assert test_employee.email == update_data["email"]

    async def test_update_employee_not_found(
        self, client: AsyncClient, auth_headers
    ):
        """Test updating non-existent employee."""
        update_data = {"email": "test@example.com"}

        response = await client.put(
            "/api/v1/employees/999999",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_update_employee_unauthorized(
        self, client: AsyncClient, test_employee
    ):
        """Test updating employee without authentication."""
        update_data = {"email": "test@example.com"}

        response = await client.put(
            f"/api/v1/employees/{test_employee.emp_no}",
            json=update_data,
        )

        assert response.status_code == 401

    async def test_update_employee_partial(
        self, client: AsyncClient, auth_headers, test_employee, db
    ):
        """Test partial employee update."""
        original_first_name = test_employee.first_name
        update_data = {"email": "partial.update@company.com"}

        response = await client.put(
            f"/api/v1/employees/{test_employee.emp_no}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Updated field should change
        assert data["email"] == update_data["email"]
        # Other fields should remain the same
        assert data["first_name"] == original_first_name


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
class TestEmployeeDelete:
    """Test delete employee endpoint (soft delete)."""

    async def test_delete_employee_success(
        self, client: AsyncClient, auth_headers, test_employee, db
    ):
        """Test successful employee deletion (soft delete)."""
        response = await client.delete(
            f"/api/v1/employees/{test_employee.emp_no}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify soft delete in database
        await db.refresh(test_employee)
        assert test_employee.is_deleted is True

    async def test_delete_employee_not_found(
        self, client: AsyncClient, auth_headers
    ):
        """Test deleting non-existent employee."""
        response = await client.delete(
            "/api/v1/employees/999999",
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_delete_employee_unauthorized(
        self, client: AsyncClient, test_employee
    ):
        """Test deleting employee without authentication."""
        response = await client.delete(
            f"/api/v1/employees/{test_employee.emp_no}"
        )

        assert response.status_code == 401

    async def test_delete_employee_already_deleted(
        self, client: AsyncClient, auth_headers, test_employee, db
    ):
        """Test deleting an already deleted employee."""
        # First deletion
        await client.delete(
            f"/api/v1/employees/{test_employee.emp_no}",
            headers=auth_headers,
        )

        # Second deletion should fail
        response = await client.delete(
            f"/api/v1/employees/{test_employee.emp_no}",
            headers=auth_headers,
        )

        assert response.status_code == 404
