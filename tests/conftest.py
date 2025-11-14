"""
Pytest Configuration
Fixtures and configuration for all tests
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator:
    """
    Create a test database session.

    Yields:
        AsyncSession: Database session for testing
    """
    # TODO: Implement actual database session fixture
    # This is a template
    yield None


@pytest.fixture
async def test_client() -> AsyncGenerator:
    """
    Create a test client for API testing.

    Yields:
        AsyncClient: HTTP client for testing
    """
    # TODO: Implement actual test client fixture
    yield None


# Add more fixtures as needed for your tests
