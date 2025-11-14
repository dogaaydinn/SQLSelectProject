"""
Audit Log ORM Model
"""
from datetime import datetime
from typing import Dict, Optional
import enum

from sqlalchemy import BigInteger, Column, DateTime, Enum as SQLEnum, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import INET, JSONB

from .base import Base


class AuditAction(str, enum.Enum):
    """Audit action enum matching database type"""

    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class AuditLog(Base):
    """Audit log model for tracking changes"""

    __tablename__ = "audit_log"

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Record Information
    table_name = Column(String(100), nullable=False)
    record_id = Column(Integer, nullable=False)

    # Action
    action = Column(SQLEnum(AuditAction, name="audit_action"), nullable=False)

    # Values (before and after)
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)

    # Audit Information
    changed_by = Column(Integer, nullable=True)
    changed_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # Request Information
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    session_id = Column(String(255), nullable=True)

    # Metadata
    metadata = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, table='{self.table_name}', record_id={self.record_id}, action={self.action})>"
