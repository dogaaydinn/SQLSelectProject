"""
User, Role, and Authentication Models
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base import Base, TimeStampMixin, UUIDMixin


class User(Base, UUIDMixin, TimeStampMixin):
    """User model for application authentication"""

    __tablename__ = "users"

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Authentication
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)

    # Personal Information
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("TRUE"))
    is_superuser = Column(Boolean, nullable=False, default=False, server_default=text("FALSE"))

    # Login Information
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0, server_default=text("0"))
    locked_until = Column(DateTime, nullable=True)

    # Metadata
    metadata = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

    # Relationships
    roles = relationship("Role", secondary="user_roles", back_populates="users", lazy="selectin")
    api_keys = relationship("ApiKey", back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}', is_active={self.is_active})>"

    @property
    def full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    @property
    def is_locked(self) -> bool:
        """Check if user account is locked"""
        if self.locked_until:
            return self.locked_until > datetime.utcnow()
        return False

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        if self.is_superuser:
            return True

        for role in self.roles:
            if role.is_active and permission in role.permissions:
                return True

        return False

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role"""
        return any(role.name == role_name and role.is_active for role in self.roles)


class Role(Base, TimeStampMixin):
    """Role model for RBAC"""

    __tablename__ = "roles"

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Role Information
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # Permissions (JSON array of permission strings)
    permissions = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))

    # Status
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("TRUE"))

    # Relationships
    users = relationship("User", secondary="user_roles", back_populates="roles", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}', is_active={self.is_active})>"


class UserRole(Base):
    """User-Role mapping table"""

    __tablename__ = "user_roles"

    # Composite Primary Key
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id = Column(
        Integer,
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Audit Information
    granted_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    granted_by = Column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"


class ApiKey(Base, TimeStampMixin):
    """API Key model for programmatic access"""

    __tablename__ = "api_keys"

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Key Information
    key_hash = Column(Text, nullable=False, unique=True)
    name = Column(String(100), nullable=False)

    # Foreign Keys
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Scopes (JSON array of scope strings)
    scopes = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))

    # Status
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("TRUE"))

    # Expiration
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, name='{self.name}', user_id={self.user_id}, is_active={self.is_active})>"

    @property
    def is_expired(self) -> bool:
        """Check if API key is expired"""
        if self.expires_at:
            return self.expires_at < datetime.utcnow()
        return False

    @property
    def is_valid(self) -> bool:
        """Check if API key is valid (active and not expired)"""
        return self.is_active and not self.is_expired
