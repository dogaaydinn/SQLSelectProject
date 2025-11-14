"""
Pydantic Schemas Package
Data validation and serialization schemas
"""

# Employee schemas
from app.schemas.employee import (
    EmployeeBase,
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    EmployeeFilter,
    PaginatedResponse,
)

# Department schemas
from app.schemas.department import (
    DepartmentBase,
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    DepartmentStatistics,
)

# Salary schemas
from app.schemas.salary import (
    SalaryBase,
    SalaryCreate,
    SalaryUpdate,
    SalaryResponse,
    SalaryWithEmployee,
)

# Analytics schemas
from app.schemas.analytics import (
    SalaryStatistics,
    SalaryDistribution,
    DepartmentPerformance,
    EmployeeTrends,
    GenderDiversity,
    TitleDistribution,
    AnalyticsSummary,
)

__all__ = [
    # Employee
    "EmployeeBase",
    "EmployeeCreate",
    "EmployeeUpdate",
    "EmployeeResponse",
    "EmployeeFilter",
    "PaginatedResponse",
    # Department
    "DepartmentBase",
    "DepartmentCreate",
    "DepartmentUpdate",
    "DepartmentResponse",
    "DepartmentStatistics",
    # Salary
    "SalaryBase",
    "SalaryCreate",
    "SalaryUpdate",
    "SalaryResponse",
    "SalaryWithEmployee",
    # Analytics
    "SalaryStatistics",
    "SalaryDistribution",
    "DepartmentPerformance",
    "EmployeeTrends",
    "GenderDiversity",
    "TitleDistribution",
    "AnalyticsSummary",
]
