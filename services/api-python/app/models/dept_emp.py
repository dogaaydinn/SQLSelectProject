"""
DeptEmp ORM Model (Employee-Department Mapping)
"""
from datetime import date
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base import Base, SoftDeleteMixin, TimeStampMixin, UUIDMixin, VersionMixin


class DeptEmp(Base, UUIDMixin, TimeStampMixin, SoftDeleteMixin, VersionMixin):
    """Department-Employee mapping model with history tracking"""

    __tablename__ = "dept_emp"

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign Keys
    emp_no = Column(
        Integer,
        ForeignKey("employees.emp_no", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    dept_no = Column(
        String(4),
        ForeignKey("departments.dept_no", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    # Date Range
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False, default=date(9999, 12, 31), server_default="'9999-12-31'")

    # Additional Information
    is_primary = Column(Boolean, nullable=False, default=True, server_default=text("TRUE"))
    title = Column(String(100), nullable=True)

    # Metadata
    metadata = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

    # Relationships
    employee = relationship("Employee", back_populates="dept_emps")
    department = relationship("Department", back_populates="dept_emps")

    # Constraints
    __table_args__ = (
        CheckConstraint("to_date >= from_date", name="chk_dept_emp_dates"),
        UniqueConstraint("emp_no", "dept_no", "from_date", name="uq_dept_emp_active"),
    )

    def __repr__(self) -> str:
        return f"<DeptEmp(id={self.id}, emp_no={self.emp_no}, dept_no='{self.dept_no}', from_date={self.from_date})>"

    @property
    def is_current(self) -> bool:
        """Check if this is the current department assignment"""
        return self.to_date.year == 9999 and not self.is_deleted
