"""
Title ORM Model
"""
from datetime import date
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import Base, SoftDeleteMixin, TimeStampMixin, UUIDMixin, VersionMixin


class Title(Base, UUIDMixin, TimeStampMixin, SoftDeleteMixin, VersionMixin):
    """Title model for employee job titles"""

    __tablename__ = "titles"

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign Keys
    emp_no = Column(
        Integer,
        ForeignKey("employees.emp_no", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    # Title Information
    title = Column(String(100), nullable=False)
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, default=date(9999, 12, 31), server_default="'9999-12-31'")

    # Relationships
    employee = relationship("Employee", back_populates="titles")

    # Constraints
    __table_args__ = (
        CheckConstraint("to_date >= from_date", name="chk_titles_dates"),
        UniqueConstraint("emp_no", "from_date", name="uq_titles_active"),
    )

    def __repr__(self) -> str:
        return f"<Title(id={self.id}, emp_no={self.emp_no}, title='{self.title}', from_date={self.from_date})>"

    @property
    def is_current(self) -> bool:
        """Check if this is the current title"""
        return self.to_date.year == 9999 and not self.is_deleted
