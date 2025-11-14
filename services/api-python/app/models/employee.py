"""
Employee SQLAlchemy Models
"""

from datetime import date, datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Boolean,
    Text, Enum, CheckConstraint, Index, DECIMAL, CHAR, JSON
)
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from app.core.database import Base


class GenderEnum(str, enum.Enum):
    """Gender enumeration."""
    MALE = "M"
    FEMALE = "F"
    OTHER = "Other"
    PREFER_NOT_TO_SAY = "PreferNotToSay"


class EmploymentStatusEnum(str, enum.Enum):
    """Employment status enumeration."""
    ACTIVE = "Active"
    TERMINATED = "Terminated"
    ON_LEAVE = "OnLeave"
    SUSPENDED = "Suspended"


class Employee(Base):
    """Employee model."""

    __tablename__ = "employees"

    emp_no = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True)
    birth_date = Column(Date, nullable=False)
    first_name = Column(String(50), nullable=False, index=True)
    last_name = Column(String(50), nullable=False, index=True)
    middle_name = Column(String(50))
    gender = Column(Enum(GenderEnum), nullable=False, default=GenderEnum.PREFER_NOT_TO_SAY)
    hire_date = Column(Date, nullable=False, index=True)
    termination_date = Column(Date)
    status = Column(
        Enum(EmploymentStatusEnum),
        nullable=False,
        default=EmploymentStatusEnum.ACTIVE,
        index=True,
    )
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(20))
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100), default="USA")
    postal_code = Column(String(20))
    ssn_encrypted = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(Integer)
    updated_by = Column(Integer)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime)
    metadata = Column(JSON, default=dict)

    __table_args__ = (
        CheckConstraint("birth_date >= '1930-01-01'", name="chk_birth_date_min"),
        CheckConstraint("hire_date >= '1980-01-01'", name="chk_hire_date_min"),
        CheckConstraint(
            "termination_date IS NULL OR termination_date >= hire_date",
            name="chk_termination_after_hire",
        ),
        Index("idx_emp_active", "status", postgresql_where="is_deleted = FALSE"),
        Index("idx_emp_full_name", "last_name", "first_name", postgresql_where="is_deleted = FALSE"),
    )

    def __repr__(self) -> str:
        return f"<Employee(emp_no={self.emp_no}, name='{self.first_name} {self.last_name}')>"


class Department(Base):
    """Department model."""

    __tablename__ = "departments"

    dept_no = Column(CHAR(4), primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True)
    dept_name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    manager_emp_no = Column(Integer, index=True)
    budget = Column(DECIMAL(15, 2))
    location = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(Integer)
    updated_by = Column(Integer)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime)
    metadata = Column(JSON, default=dict)

    def __repr__(self) -> str:
        return f"<Department(dept_no='{self.dept_no}', name='{self.dept_name}')>"


class DepartmentEmployee(Base):
    """Department-Employee mapping model."""

    __tablename__ = "dept_emp"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True)
    emp_no = Column(Integer, nullable=False, index=True)
    dept_no = Column(CHAR(4), nullable=False, index=True)
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, default=date(9999, 12, 31), nullable=False)
    is_primary = Column(Boolean, default=True, nullable=False)
    title = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(Integer)
    updated_by = Column(Integer)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime)
    metadata = Column(JSON, default=dict)

    __table_args__ = (
        CheckConstraint("to_date >= from_date", name="chk_dept_emp_dates"),
        Index("idx_dept_emp_current", "emp_no", "dept_no",
              postgresql_where="to_date = '9999-12-31' AND is_deleted = FALSE"),
    )

    def __repr__(self) -> str:
        return f"<DepartmentEmployee(emp_no={self.emp_no}, dept_no='{self.dept_no}')>"


class Salary(Base):
    """Salary model."""

    __tablename__ = "salaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True)
    emp_no = Column(Integer, nullable=False, index=True)
    salary = Column(DECIMAL(12, 2), nullable=False, index=True)
    currency = Column(CHAR(3), default="USD", nullable=False)
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, default=date(9999, 12, 31), nullable=False)
    salary_type = Column(String(50), default="Base")
    bonus = Column(DECIMAL(12, 2), default=0)
    commission = Column(DECIMAL(12, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(Integer)
    updated_by = Column(Integer)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime)
    metadata = Column(JSON, default=dict)

    __table_args__ = (
        CheckConstraint("salary > 0", name="chk_salary_positive"),
        CheckConstraint("to_date >= from_date", name="chk_salary_dates"),
        Index("idx_salary_current", "emp_no", "from_date",
              postgresql_where="to_date = '9999-12-31' AND is_deleted = FALSE"),
    )

    def __repr__(self) -> str:
        return f"<Salary(emp_no={self.emp_no}, salary={self.salary})>"
