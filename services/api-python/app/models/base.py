"""
Base models and mixins for SQLAlchemy ORM
"""
from datetime import datetime
from typing import Any
from uuid import UUID as UUIDType, uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

# Create base class for all models
Base = declarative_base()


class UUIDMixin:
    """Mixin to add UUID column to models"""

    uuid = Column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
        default=uuid4,
        server_default=text("uuid_generate_v4()"),
    )


class TimeStampMixin:
    """Mixin to add timestamp columns to models"""

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)


class SoftDeleteMixin:
    """Mixin to add soft delete functionality"""

    is_deleted = Column(Boolean, nullable=False, default=False, server_default=text("FALSE"))
    deleted_at = Column(DateTime, nullable=True)


class VersionMixin:
    """Mixin to add version tracking (optimistic locking)"""

    version = Column(Integer, nullable=False, default=1, server_default=text("1"))
