"""
Database Connection Management
Provides async database connections and session management
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings
from app.core.logging import logger


# Create async engine
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    poolclass=QueuePool if settings.ENVIRONMENT == "production" else NullPool,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def init_db_connections() -> None:
    """Initialize database connections."""
    try:
        async with engine.begin() as conn:
            # Test connection
            await conn.execute("SELECT 1")
        logger.info("Database connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database connections: {e}")
        raise


async def close_db_connections() -> None:
    """Close database connections."""
    try:
        await engine.dispose()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides async database session.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def execute_raw_query(query: str, params: dict = None) -> list:
    """
    Execute raw SQL query.

    Args:
        query: SQL query string
        params: Query parameters

    Returns:
        List of query results
    """
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(query, params or {})
            await session.commit()
            return result.fetchall()
        except Exception as e:
            await session.rollback()
            logger.error(f"Error executing raw query: {e}")
            raise


class DatabaseHealthCheck:
    """Database health check utility."""

    @staticmethod
    async def check() -> dict:
        """
        Check database connection health.

        Returns:
            dict: Health status information
        """
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute("SELECT 1")
                row = result.fetchone()

                if row and row[0] == 1:
                    return {
                        "status": "healthy",
                        "database": "connected",
                        "pool_size": engine.pool.size(),
                        "checked_out": engine.pool.checked_out_connections,
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "database": "query_failed",
                    }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "database": "connection_failed",
                "error": str(e),
            }
