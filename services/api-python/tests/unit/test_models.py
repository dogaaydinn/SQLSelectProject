"""
Unit Tests for ORM Models
Tests model creation, relationships, properties, and methods
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee, EmploymentStatus, GenderType
from app.models.department import Department
from app.models.salary import Salary
from app.models.title import Title
from app.models.dept_emp import DeptEmp
from app.models.user import User, Role, UserRole, ApiKey


# ==========================================
# Employee Model Tests
# ==========================================

@pytest.mark.unit
@pytest.mark.database
class TestEmployeeModel:
    """Test Employee model."""

    @pytest.mark.asyncio
    async def test_create_employee(self, db_session: AsyncSession):
        """Test creating an employee."""
        employee = Employee(
            birth_date=date(1990, 1, 1),
            first_name="Test",
            last_name="Employee",
            gender=GenderType.M,
            hire_date=date(2020, 1, 1),
            status=EmploymentStatus.Active,
        )

        db_session.add(employee)
        await db_session.commit()
        await db_session.refresh(employee)

        assert employee.emp_no is not None
        assert employee.uuid is not None
        assert employee.first_name == "Test"
        assert employee.last_name == "Employee"
        assert employee.is_deleted is False

    @pytest.mark.asyncio
    async def test_employee_full_name(self, test_employee: Employee):
        """Test employee full name property."""
        assert test_employee.full_name == "John Doe"

        # Test with middle name
        test_employee.middle_name = "Middle"
        assert test_employee.full_name == "John Middle Doe"

    @pytest.mark.asyncio
    async def test_employee_is_active(self, test_employee: Employee):
        """Test employee is_active property."""
        assert test_employee.is_active is True

        # Test terminated employee
        test_employee.status = EmploymentStatus.Terminated
        assert test_employee.is_active is False

        # Test deleted employee
        test_employee.status = EmploymentStatus.Active
        test_employee.is_deleted = True
        assert test_employee.is_active is False

    @pytest.mark.asyncio
    async def test_employee_relationships(
        self,
        db_session: AsyncSession,
        test_employee: Employee,
        test_salary: Salary,
    ):
        """Test employee relationships."""
        await db_session.refresh(test_employee)
        assert len(test_employee.salaries) > 0
        assert test_employee.salaries[0].emp_no == test_employee.emp_no


# ==========================================
# Department Model Tests
# ==========================================

@pytest.mark.unit
@pytest.mark.database
class TestDepartmentModel:
    """Test Department model."""

    @pytest.mark.asyncio
    async def test_create_department(self, db_session: AsyncSession):
        """Test creating a department."""
        dept = Department(
            dept_no="d002",
            dept_name="Sales",
            description="Sales Department",
            budget=Decimal("750000.00"),
        )

        db_session.add(dept)
        await db_session.commit()
        await db_session.refresh(dept)

        assert dept.dept_no == "d002"
        assert dept.uuid is not None
        assert dept.dept_name == "Sales"
        assert dept.is_active is True

    @pytest.mark.asyncio
    async def test_department_employee_count(
        self,
        db_session: AsyncSession,
        test_department: Department,
        test_dept_emp: DeptEmp,
    ):
        """Test department employee_count property."""
        await db_session.refresh(test_department)
        assert test_department.employee_count >= 0


# ==========================================
# Salary Model Tests
# ==========================================

@pytest.mark.unit
@pytest.mark.database
class TestSalaryModel:
    """Test Salary model."""

    @pytest.mark.asyncio
    async def test_create_salary(
        self,
        db_session: AsyncSession,
        test_employee: Employee,
    ):
        """Test creating a salary record."""
        salary = Salary(
            emp_no=test_employee.emp_no,
            salary=Decimal("85000.00"),
            currency="USD",
            from_date=date(2021, 1, 1),
            to_date=date(9999, 12, 31),
        )

        db_session.add(salary)
        await db_session.commit()
        await db_session.refresh(salary)

        assert salary.id is not None
        assert salary.salary == Decimal("85000.00")
        assert salary.is_deleted is False

    @pytest.mark.asyncio
    async def test_salary_total_compensation(self, test_salary: Salary):
        """Test salary total_compensation property."""
        expected = test_salary.salary + test_salary.bonus + test_salary.commission
        assert test_salary.total_compensation == expected

    @pytest.mark.asyncio
    async def test_salary_is_current(self, test_salary: Salary):
        """Test salary is_current property."""
        assert test_salary.is_current is True

        # Test past salary
        test_salary.to_date = date(2021, 12, 31)
        assert test_salary.is_current is False


# ==========================================
# Title Model Tests
# ==========================================

@pytest.mark.unit
@pytest.mark.database
class TestTitleModel:
    """Test Title model."""

    @pytest.mark.asyncio
    async def test_create_title(
        self,
        db_session: AsyncSession,
        test_employee: Employee,
    ):
        """Test creating a title record."""
        title = Title(
            emp_no=test_employee.emp_no,
            title="Senior Engineer",
            from_date=date(2020, 1, 1),
            to_date=date(9999, 12, 31),
        )

        db_session.add(title)
        await db_session.commit()
        await db_session.refresh(title)

        assert title.id is not None
        assert title.title == "Senior Engineer"

    @pytest.mark.asyncio
    async def test_title_is_current(
        self,
        db_session: AsyncSession,
        test_employee: Employee,
    ):
        """Test title is_current property."""
        title = Title(
            emp_no=test_employee.emp_no,
            title="Engineer",
            from_date=date(2020, 1, 1),
            to_date=date(9999, 12, 31),
        )

        db_session.add(title)
        await db_session.commit()

        assert title.is_current is True


# ==========================================
# User Model Tests
# ==========================================

@pytest.mark.unit
@pytest.mark.database
class TestUserModel:
    """Test User model."""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession):
        """Test creating a user."""
        user = User(
            username="newuser",
            email="newuser@example.com",
            password_hash="hashed_password",
            is_active=True,
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.id is not None
        assert user.username == "newuser"
        assert user.is_superuser is False

    @pytest.mark.asyncio
    async def test_user_full_name(self, test_user: User):
        """Test user full_name property."""
        # Without first/last name
        test_user.first_name = None
        test_user.last_name = None
        assert test_user.full_name == test_user.username

        # With first/last name
        test_user.first_name = "Test"
        test_user.last_name = "User"
        assert test_user.full_name == "Test User"

    @pytest.mark.asyncio
    async def test_user_is_locked(self, test_user: User):
        """Test user is_locked property."""
        assert test_user.is_locked is False

        # Lock user
        test_user.locked_until = datetime.utcnow().replace(year=2099)
        assert test_user.is_locked is True

    @pytest.mark.asyncio
    async def test_user_has_permission(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test user permission checking."""
        # Create role with permissions
        role = Role(
            name="test_role",
            permissions=["read:data", "write:data"],
            is_active=True,
        )
        db_session.add(role)
        await db_session.commit()
        await db_session.refresh(role)

        # Assign role to user
        test_user.roles.append(role)
        await db_session.commit()
        await db_session.refresh(test_user)

        assert test_user.has_permission("read:data") is True
        assert test_user.has_permission("write:data") is True
        assert test_user.has_permission("delete:data") is False

    @pytest.mark.asyncio
    async def test_user_has_role(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test user role checking."""
        role = Role(
            name="manager",
            is_active=True,
        )
        db_session.add(role)
        await db_session.commit()
        await db_session.refresh(role)

        test_user.roles.append(role)
        await db_session.commit()
        await db_session.refresh(test_user)

        assert test_user.has_role("manager") is True
        assert test_user.has_role("admin") is False

    @pytest.mark.asyncio
    async def test_superuser_permissions(self, test_superuser: User):
        """Test superuser always has all permissions."""
        assert test_superuser.has_permission("any:permission") is True


# ==========================================
# API Key Model Tests
# ==========================================

@pytest.mark.unit
@pytest.mark.database
class TestApiKeyModel:
    """Test ApiKey model."""

    @pytest.mark.asyncio
    async def test_create_api_key(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test creating an API key."""
        api_key = ApiKey(
            key_hash="hashed_api_key",
            user_id=test_user.id,
            name="Test API Key",
            scopes=["read", "write"],
            is_active=True,
        )

        db_session.add(api_key)
        await db_session.commit()
        await db_session.refresh(api_key)

        assert api_key.id is not None
        assert api_key.name == "Test API Key"

    @pytest.mark.asyncio
    async def test_api_key_is_expired(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test API key expiration."""
        api_key = ApiKey(
            key_hash="hashed_key",
            user_id=test_user.id,
            name="Expiring Key",
            is_active=True,
        )

        db_session.add(api_key)
        await db_session.commit()

        # Not expired (no expiration date)
        assert api_key.is_expired is False

        # Set past expiration
        api_key.expires_at = datetime.utcnow().replace(year=2000)
        assert api_key.is_expired is True

    @pytest.mark.asyncio
    async def test_api_key_is_valid(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test API key validity."""
        api_key = ApiKey(
            key_hash="hashed_key",
            user_id=test_user.id,
            name="Valid Key",
            is_active=True,
        )

        db_session.add(api_key)
        await db_session.commit()

        assert api_key.is_valid is True

        # Inactive key
        api_key.is_active = False
        assert api_key.is_valid is False

        # Expired key
        api_key.is_active = True
        api_key.expires_at = datetime.utcnow().replace(year=2000)
        assert api_key.is_valid is False
