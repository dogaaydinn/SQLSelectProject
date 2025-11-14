"""
Department ORM Model
"""
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, CheckConstraint, Column, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base import Base, SoftDeleteMixin, TimeStampMixin, UUIDMixin, VersionMixin


class Department(Base, UUIDMixin, TimeStampMixin, SoftDeleteMixin, VersionMixin):
    """Department model with hierarchy support"""

    __tablename__ = "departments"

    # Primary Key
    dept_no = Column(String(4), primary_key=True)

    # Basic Information
    dept_name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # Management
    manager_emp_no = Column(Integer, nullable=True)

    # Budget
    budget = Column(Numeric(15, 2), nullable=True)

    # Location
    location = Column(String(255), nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("TRUE"))

    # Metadata
    metadata = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

    # Relationships
    dept_emps = relationship("DeptEmp", back_populates="department", lazy="selectin")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "LENGTH(TRIM(dept_name)) > 0",
            name="chk_departments_dept_name",
        ),
    )

    def __repr__(self) -> str:
        return f"<Department(dept_no='{self.dept_no}', name='{self.dept_name}', is_active={self.is_active})>"

    @property
    def employee_count(self) -> int:
        """Get count of active employees in department"""
        return len([de for de in self.dept_emps if de.to_date.year == 9999 and not de.is_deleted])
