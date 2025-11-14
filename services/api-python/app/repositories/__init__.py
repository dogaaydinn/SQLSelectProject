"""
Repository Layer
Provides data access abstraction using the Repository Pattern
"""

from app.repositories.base import BaseRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.department_repository import DepartmentRepository
from app.repositories.salary_repository import SalaryRepository
from app.repositories.user_repository import UserRepository, RoleRepository

__all__ = [
    "BaseRepository",
    "EmployeeRepository",
    "DepartmentRepository",
    "SalaryRepository",
    "UserRepository",
    "RoleRepository",
]
