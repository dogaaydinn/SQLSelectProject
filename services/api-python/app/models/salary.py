"""
Salary ORM Model
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base import Base, SoftDeleteMixin, TimeStampMixin, UUIDMixin, VersionMixin


class Salary(Base, UUIDMixin, TimeStampMixin, SoftDeleteMixin, VersionMixin):
    """Salary model with history tracking"""

    __tablename__ = "salaries"

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Keys
    emp_no = Column(
        Integer,
        ForeignKey("employees.emp_no", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    # Salary Information
    salary = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD", server_default="USD")
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False, default=date(9999, 12, 31), server_default="'9999-12-31'")

    # Salary Type and Additional Compensation
    salary_type = Column(String(50), default="Base", server_default="Base")
    bonus = Column(Numeric(12, 2), default=Decimal(0), server_default=text("0"))
    commission = Column(Numeric(12, 2), default=Decimal(0), server_default=text("0"))

    # Metadata
    metadata = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

    # Relationships
    employee = relationship("Employee", back_populates="salaries")

    # Constraints
    __table_args__ = (
        CheckConstraint("salary > 0", name="chk_salaries_salary"),
        CheckConstraint("to_date >= from_date", name="chk_salaries_dates"),
        UniqueConstraint("emp_no", "from_date", name="uq_salaries_active"),
    )

    def __repr__(self) -> str:
        return f"<Salary(id={self.id}, emp_no={self.emp_no}, salary={self.salary}, from_date={self.from_date})>"

    @property
    def total_compensation(self) -> Decimal:
        """Calculate total compensation including bonus and commission"""
        return self.salary + (self.bonus or Decimal(0)) + (self.commission or Decimal(0))

    @property
    def is_current(self) -> bool:
        """Check if this is the current salary"""
        return self.to_date.year == 9999 and not self.is_deleted
