"""
Integration Tests for Department API Endpoints
Tests all CRUD operations, statistics, and employee relationships
"""

import pytest
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy import select

from app.models.department import Department


@pytest.mark.integration
@pytest.mark.api
class TestDepartmentList:
    """Test department list endpoint."""

    async def test_list_departments_success(self, client: AsyncClient):
        """Test successful department list retrieval."""
        response = await client.get("/api/v1/departments")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["items"], list)

    async def test_list_departments_pagination(self, client: AsyncClient):
        """Test department list with pagination."""
        response = await client.get("/api/v1/departments?page=1&page_size=3")

        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 1
        assert data["page_size"] == 3
        assert len(data["items"]) <= 3

    async def test_list_departments_search(
        self, client: AsyncClient, test_department
    ):
        """Test department search functionality."""
        response = await client.get(
            f"/api/v1/departments?search={test_department.dept_name}"
        )

        assert response.status_code == 200
        data = response.json()

        # Should find at least the test department
        assert data["total"] >= 1
        found = any(
            item["dept_no"] == test_department.dept_no
            for item in data["items"]
        )
        assert found

    async def test_list_departments_filter_active(self, client: AsyncClient):
        """Test filtering departments by active status."""
        response = await client.get("/api/v1/departments?is_active=true")

        assert response.status_code == 200
        data = response.json()

        # All returned departments should be active
        for item in data["items"]:
            assert item["is_active"] is True


@pytest.mark.integration
@pytest.mark.api
class TestDepartmentGet:
    """Test get single department endpoint."""

    async def test_get_department_success(
        self, client: AsyncClient, test_department
    ):
        """Test successful department retrieval."""
        response = await client.get(f"/api/v1/departments/{test_department.dept_no}")

        assert response.status_code == 200
        data = response.json()

        assert data["dept_no"] == test_department.dept_no
        assert data["dept_name"] == test_department.dept_name
        assert "uuid" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_get_department_not_found(self, client: AsyncClient):
        """Test getting non-existent department."""
        response = await client.get("/api/v1/departments/d999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    async def test_get_department_caching(
        self, client: AsyncClient, test_department
    ):
        """Test that department retrieval uses caching."""
        # First request
        response1 = await client.get(f"/api/v1/departments/{test_department.dept_no}")
        assert response1.status_code == 200

        # Second request - should hit cache
        response2 = await client.get(f"/api/v1/departments/{test_department.dept_no}")
        assert response2.status_code == 200

        # Data should be identical
        assert response1.json() == response2.json()


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
class TestDepartmentCreate:
    """Test create department endpoint."""

    async def test_create_department_success(
        self, client: AsyncClient, auth_headers, db
    ):
        """Test successful department creation."""
        department_data = {
            "dept_no": "d999",
            "dept_name": "Test Department",
            "description": "A test department",
            "budget": "1000000.00",
            "location": "Test Building",
            "is_active": True,
        }

        response = await client.post(
            "/api/v1/departments",
            json=department_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        assert data["dept_no"] == department_data["dept_no"]
        assert data["dept_name"] == department_data["dept_name"]
        assert data["description"] == department_data["description"]
        assert "uuid" in data

        # Verify in database
        stmt = select(Department).where(Department.dept_no == data["dept_no"])
        result = await db.execute(stmt)
        department = result.scalar_one_or_none()
        assert department is not None
        assert department.dept_name == department_data["dept_name"]

    async def test_create_department_duplicate(
        self, client: AsyncClient, auth_headers, test_department
    ):
        """Test creating department with duplicate dept_no."""
        department_data = {
            "dept_no": test_department.dept_no,  # Duplicate
            "dept_name": "Duplicate Department",
        }

        response = await client.post(
            "/api/v1/departments",
            json=department_data,
            headers=auth_headers,
        )

        assert response.status_code == 409  # Conflict

    async def test_create_department_invalid_dept_no(
        self, client: AsyncClient, auth_headers
    ):
        """Test creating department with invalid dept_no format."""
        department_data = {
            "dept_no": "invalid",  # Should be d###
            "dept_name": "Test Department",
        }

        response = await client.post(
            "/api/v1/departments",
            json=department_data,
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error

    async def test_create_department_unauthorized(self, client: AsyncClient):
        """Test creating department without authentication."""
        department_data = {
            "dept_no": "d998",
            "dept_name": "Unauthorized Department",
        }

        response = await client.post("/api/v1/departments", json=department_data)

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
class TestDepartmentUpdate:
    """Test update department endpoint."""

    async def test_update_department_success(
        self, client: AsyncClient, auth_headers, test_department, db
    ):
        """Test successful department update."""
        update_data = {
            "dept_name": "Updated Department Name",
            "description": "Updated description",
            "budget": "2000000.00",
        }

        response = await client.put(
            f"/api/v1/departments/{test_department.dept_no}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["dept_no"] == test_department.dept_no
        assert data["dept_name"] == update_data["dept_name"]
        assert data["description"] == update_data["description"]

        # Verify in database
        await db.refresh(test_department)
        assert test_department.dept_name == update_data["dept_name"]

    async def test_update_department_partial(
        self, client: AsyncClient, auth_headers, test_department, db
    ):
        """Test partial department update."""
        original_dept_name = test_department.dept_name
        update_data = {"description": "Only update description"}

        response = await client.put(
            f"/api/v1/departments/{test_department.dept_no}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Updated field should change
        assert data["description"] == update_data["description"]
        # Other fields should remain the same
        assert data["dept_name"] == original_dept_name

    async def test_update_department_not_found(
        self, client: AsyncClient, auth_headers
    ):
        """Test updating non-existent department."""
        update_data = {"dept_name": "Non-existent"}

        response = await client.put(
            "/api/v1/departments/d999",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_update_department_unauthorized(
        self, client: AsyncClient, test_department
    ):
        """Test updating department without authentication."""
        update_data = {"dept_name": "Unauthorized Update"}

        response = await client.put(
            f"/api/v1/departments/{test_department.dept_no}",
            json=update_data,
        )

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
class TestDepartmentDelete:
    """Test delete department endpoint (soft delete)."""

    async def test_delete_department_success(
        self, client: AsyncClient, auth_headers, test_department, db
    ):
        """Test successful department deletion (soft delete)."""
        response = await client.delete(
            f"/api/v1/departments/{test_department.dept_no}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify soft delete in database
        await db.refresh(test_department)
        assert test_department.is_deleted is True

    async def test_delete_department_not_found(
        self, client: AsyncClient, auth_headers
    ):
        """Test deleting non-existent department."""
        response = await client.delete(
            "/api/v1/departments/d999",
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_delete_department_unauthorized(
        self, client: AsyncClient, test_department
    ):
        """Test deleting department without authentication."""
        response = await client.delete(
            f"/api/v1/departments/{test_department.dept_no}"
        )

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
class TestDepartmentEmployees:
    """Test department employees endpoint."""

    async def test_get_department_employees(
        self, client: AsyncClient, test_department
    ):
        """Test getting employees in a department."""
        response = await client.get(
            f"/api/v1/departments/{test_department.dept_no}/employees"
        )

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_get_department_employees_pagination(
        self, client: AsyncClient, test_department
    ):
        """Test department employees with pagination."""
        response = await client.get(
            f"/api/v1/departments/{test_department.dept_no}/employees?page=1&page_size=5"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 1
        assert data["page_size"] == 5
        assert len(data["items"]) <= 5

    async def test_get_department_employees_not_found(self, client: AsyncClient):
        """Test getting employees for non-existent department."""
        response = await client.get("/api/v1/departments/d999/employees")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.database
class TestDepartmentStatistics:
    """Test department statistics endpoint."""

    async def test_get_department_statistics(
        self, client: AsyncClient, test_department
    ):
        """Test getting department statistics."""
        response = await client.get(
            f"/api/v1/departments/{test_department.dept_no}/statistics"
        )

        assert response.status_code == 200
        data = response.json()

        assert "dept_no" in data
        assert "dept_name" in data
        assert "employee_count" in data
        assert data["dept_no"] == test_department.dept_no

    async def test_get_department_statistics_caching(
        self, client: AsyncClient, test_department
    ):
        """Test that department statistics uses caching."""
        # First request
        response1 = await client.get(
            f"/api/v1/departments/{test_department.dept_no}/statistics"
        )
        assert response1.status_code == 200

        # Second request - should hit cache
        response2 = await client.get(
            f"/api/v1/departments/{test_department.dept_no}/statistics"
        )
        assert response2.status_code == 200

        # Data should be identical
        assert response1.json() == response2.json()

    async def test_get_department_statistics_not_found(self, client: AsyncClient):
        """Test getting statistics for non-existent department."""
        response = await client.get("/api/v1/departments/d999/statistics")

        assert response.status_code == 404
