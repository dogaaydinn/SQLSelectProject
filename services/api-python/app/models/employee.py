"""
Employee ORM Model
"""
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    Enum as SQLEnum,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base import Base, SoftDeleteMixin, TimeStampMixin, UUIDMixin, VersionMixin

import enum


class GenderType(str, enum.Enum):
    """Gender enum matching database type"""

    M = "M"
    F = "F"
    Other = "Other"
    PreferNotToSay = "PreferNotToSay"


class EmploymentStatus(str, enum.Enum):
    """Employment status enum matching database type"""

    Active = "Active"
    Terminated = "Terminated"
    OnLeave = "OnLeave"
    Suspended = "Suspended"


class Employee(Base, UUIDMixin, TimeStampMixin, SoftDeleteMixin, VersionMixin):
    """Employee model with enhanced fields and soft delete"""

    __tablename__ = "employees"

    # Primary Key
    emp_no = Column(Integer, primary_key=True, autoincrement=True)

    # Basic Information
    birth_date = Column(
        Date,
        nullable=False,
    )
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    middle_name = Column(String(50), nullable=True)

    gender = Column(
        SQLEnum(GenderType, name="gender_type"),
        nullable=False,
        default=GenderType.PreferNotToSay,
        server_default="PreferNotToSay",
    )

    # Employment Information
    hire_date = Column(Date, nullable=False)
    termination_date = Column(Date, nullable=True)
    status = Column(
        SQLEnum(EmploymentStatus, name="employment_status"),
        nullable=False,
        default=EmploymentStatus.Active,
        server_default="Active",
    )

    # Contact Information
    email = Column(String(255), unique=True, nullable=True)
    phone = Column(String(20), nullable=True)

    # Address Information
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="USA", server_default="USA")
    postal_code = Column(String(20), nullable=True)

    # Encrypted SSN
    ssn_encrypted = Column(Text, nullable=True)

    # Metadata
    metadata = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

    # Relationships
    salaries = relationship("Salary", back_populates="employee", lazy="selectin")
    titles = relationship("Title", back_populates="employee", lazy="selectin")
    dept_emps = relationship("DeptEmp", back_populates="employee", lazy="selectin")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "birth_date >= '1930-01-01' AND birth_date <= CURRENT_DATE",
            name="chk_employees_birth_date",
        ),
        CheckConstraint(
            "LENGTH(TRIM(first_name)) > 0",
            name="chk_employees_first_name",
        ),
        CheckConstraint(
            "LENGTH(TRIM(last_name)) > 0",
            name="chk_employees_last_name",
        ),
        CheckConstraint(
            "hire_date >= '1980-01-01'",
            name="chk_employees_hire_date",
        ),
        CheckConstraint(
            "termination_date IS NULL OR termination_date >= hire_date",
            name="chk_employees_termination_date",
        ),
    )

    def __repr__(self) -> str:
        return f"<Employee(emp_no={self.emp_no}, name='{self.first_name} {self.last_name}', status={self.status})>"

    @property
    def full_name(self) -> str:
        """Get employee's full name"""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    @property
    def is_active(self) -> bool:
        """Check if employee is active"""
        return self.status == EmploymentStatus.Active and not self.is_deleted
