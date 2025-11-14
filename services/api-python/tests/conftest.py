"""
Pytest Configuration and Fixtures
Provides shared fixtures for all tests
"""

import asyncio
from typing import AsyncGenerator, Generator
from datetime import date, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.config import settings
from app.core.database import get_db, Base
from app.core.security import create_access_token, hash_password
from app.models.user import User, Role
from app.models.employee import Employee, EmploymentStatus, GenderType
from app.models.department import Department
from app.models.salary import Salary
from app.models.dept_emp import DeptEmp


# ==========================================
# Async Event Loop Fixture
# ==========================================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==========================================
# Database Fixtures
# ==========================================

@pytest.fixture(scope="session")
def test_db_url() -> str:
    """Get test database URL."""
    # Use a separate test database
    return settings.DATABASE_URL.replace("/employees", "/employees_test")


@pytest_asyncio.fixture(scope="session")
async def test_engine(test_db_url: str):
    """Create test database engine."""
    engine = create_async_engine(
        test_db_url,
        echo=False,
        poolclass=NullPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for each test."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden database dependency."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ==========================================
# User & Auth Fixtures
# ==========================================

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
        first_name="Test",
        last_name="User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_superuser(db_session: AsyncSession) -> User:
    """Create a test superuser."""
    user = User(
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("adminpassword123"),
        first_name="Admin",
        last_name="User",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_role(db_session: AsyncSession) -> Role:
    """Create a test role."""
    role = Role(
        name="user",
        description="Standard user role",
        permissions=["read:employees", "read:departments"],
        is_active=True,
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


@pytest.fixture
def user_token(test_user: User) -> str:
    """Generate JWT token for test user."""
    return create_access_token(
        subject=test_user.username,
        additional_claims={
            "user_id": test_user.id,
            "email": test_user.email,
            "is_superuser": test_user.is_superuser,
        },
    )


@pytest.fixture
def superuser_token(test_superuser: User) -> str:
    """Generate JWT token for test superuser."""
    return create_access_token(
        subject=test_superuser.username,
        additional_claims={
            "user_id": test_superuser.id,
            "email": test_superuser.email,
            "is_superuser": test_superuser.is_superuser,
        },
    )


@pytest.fixture
def auth_headers(user_token: str) -> dict:
    """Get authorization headers for test user."""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(superuser_token: str) -> dict:
    """Get authorization headers for admin user."""
    return {"Authorization": f"Bearer {superuser_token}"}


# ==========================================
# Sample Data Fixtures
# ==========================================

@pytest_asyncio.fixture
async def test_department(db_session: AsyncSession) -> Department:
    """Create a test department."""
    dept = Department(
        dept_no="d001",
        dept_name="Engineering",
        description="Engineering Department",
        budget=1000000.00,
        location="San Francisco",
        is_active=True,
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)
    return dept


@pytest_asyncio.fixture
async def test_employee(db_session: AsyncSession) -> Employee:
    """Create a test employee."""
    emp = Employee(
        birth_date=date(1990, 1, 1),
        first_name="John",
        last_name="Doe",
        gender=GenderType.M,
        hire_date=date(2020, 1, 1),
        status=EmploymentStatus.Active,
        email="john.doe@example.com",
        phone="+1234567890",
    )
    db_session.add(emp)
    await db_session.commit()
    await db_session.refresh(emp)
    return emp


@pytest_asyncio.fixture
async def test_salary(db_session: AsyncSession, test_employee: Employee) -> Salary:
    """Create a test salary record."""
    salary = Salary(
        emp_no=test_employee.emp_no,
        salary=75000.00,
        currency="USD",
        from_date=date(2020, 1, 1),
        to_date=date(9999, 12, 31),
        salary_type="Base",
        bonus=5000.00,
        commission=0.00,
    )
    db_session.add(salary)
    await db_session.commit()
    await db_session.refresh(salary)
    return salary


@pytest_asyncio.fixture
async def test_dept_emp(
    db_session: AsyncSession,
    test_employee: Employee,
    test_department: Department,
) -> DeptEmp:
    """Create a test department-employee mapping."""
    dept_emp = DeptEmp(
        emp_no=test_employee.emp_no,
        dept_no=test_department.dept_no,
        from_date=date(2020, 1, 1),
        to_date=date(9999, 12, 31),
        is_primary=True,
    )
    db_session.add(dept_emp)
    await db_session.commit()
    await db_session.refresh(dept_emp)
    return dept_emp


@pytest_asyncio.fixture
async def multiple_employees(db_session: AsyncSession) -> list[Employee]:
    """Create multiple test employees."""
    employees = [
        Employee(
            birth_date=date(1985, 1, 1),
            first_name="Alice",
            last_name="Smith",
            gender=GenderType.F,
            hire_date=date(2018, 1, 1),
            status=EmploymentStatus.Active,
            email=f"alice.smith@example.com",
        ),
        Employee(
            birth_date=date(1988, 6, 15),
            first_name="Bob",
            last_name="Johnson",
            gender=GenderType.M,
            hire_date=date(2019, 3, 15),
            status=EmploymentStatus.Active,
            email=f"bob.johnson@example.com",
        ),
        Employee(
            birth_date=date(1992, 12, 30),
            first_name="Carol",
            last_name="Williams",
            gender=GenderType.F,
            hire_date=date(2021, 6, 1),
            status=EmploymentStatus.Active,
            email=f"carol.williams@example.com",
        ),
    ]

    for emp in employees:
        db_session.add(emp)

    await db_session.commit()

    for emp in employees:
        await db_session.refresh(emp)

    return employees


# ==========================================
# Utility Fixtures
# ==========================================

@pytest.fixture
def sample_employee_data() -> dict:
    """Sample employee data for creating new employees."""
    return {
        "birth_date": "1990-05-15",
        "first_name": "Jane",
        "last_name": "Doe",
        "gender": "F",
        "hire_date": "2022-01-01",
        "email": "jane.doe@example.com",
        "phone": "+1987654321",
    }


@pytest.fixture
def sample_department_data() -> dict:
    """Sample department data for creating new departments."""
    return {
        "dept_no": "d999",
        "dept_name": "Test Department",
        "description": "A test department",
        "budget": 500000.00,
        "location": "Test City",
        "is_active": True,
    }


@pytest.fixture
def sample_salary_data(test_employee: Employee) -> dict:
    """Sample salary data for creating new salary records."""
    return {
        "emp_no": test_employee.emp_no,
        "salary": 80000.00,
        "currency": "USD",
        "from_date": "2023-01-01",
        "to_date": "9999-12-31",
        "salary_type": "Base",
        "bonus": 0.00,
        "commission": 0.00,
    }


# ==========================================
# Cleanup Fixtures
# ==========================================

@pytest.fixture(autouse=True)
async def cleanup_cache():
    """Clean up cache before and after each test."""
    # This would clear Redis cache if cache_manager is available
    # For now, it's a placeholder
    yield
    # Cleanup after test
    pass
