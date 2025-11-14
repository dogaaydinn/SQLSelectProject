"""
Analytics Pydantic Schemas
Data validation and serialization for Analytics API
"""

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class SalaryStatistics(BaseModel):
    """Schema for salary statistics."""
    total_employees: int = Field(..., description="Total number of employees")
    avg_salary: Optional[Decimal] = Field(None, description="Average salary")
    min_salary: Optional[Decimal] = Field(None, description="Minimum salary")
    max_salary: Optional[Decimal] = Field(None, description="Maximum salary")
    median_salary: Optional[Decimal] = Field(None, description="Median salary")
    total_payroll: Optional[Decimal] = Field(None, description="Total payroll")
    std_deviation: Optional[float] = Field(None, description="Salary standard deviation")


class SalaryDistribution(BaseModel):
    """Schema for salary distribution by range."""
    salary_range: str = Field(..., description="Salary range")
    count: int = Field(..., description="Number of employees in range")
    percentage: float = Field(..., description="Percentage of total employees")


class DepartmentPerformance(BaseModel):
    """Schema for department performance metrics."""
    dept_no: str = Field(..., description="Department number")
    dept_name: str = Field(..., description="Department name")
    employee_count: int = Field(..., description="Number of employees")
    avg_salary: Optional[Decimal] = Field(None, description="Average salary")
    total_payroll: Optional[Decimal] = Field(None, description="Total payroll")
    budget: Optional[Decimal] = Field(None, description="Department budget")
    budget_utilization: Optional[float] = Field(None, description="Budget utilization percentage")
    avg_tenure_days: Optional[float] = Field(None, description="Average tenure in days")


class EmployeeTrends(BaseModel):
    """Schema for employee hiring and termination trends."""
    period: str = Field(..., description="Time period (year, quarter, month)")
    new_hires: int = Field(..., description="Number of new hires")
    terminations: int = Field(..., description="Number of terminations")
    net_change: int = Field(..., description="Net change in employees")
    total_employees: int = Field(..., description="Total employees at end of period")


class GenderDiversity(BaseModel):
    """Schema for gender diversity statistics."""
    gender: str = Field(..., description="Gender")
    count: int = Field(..., description="Number of employees")
    percentage: float = Field(..., description="Percentage of total employees")
    avg_salary: Optional[Decimal] = Field(None, description="Average salary for gender")


class TitleDistribution(BaseModel):
    """Schema for job title distribution."""
    title: str = Field(..., description="Job title")
    count: int = Field(..., description="Number of employees")
    percentage: float = Field(..., description="Percentage of total employees")
    avg_salary: Optional[Decimal] = Field(None, description="Average salary for title")


class AnalyticsSummary(BaseModel):
    """Schema for overall analytics summary."""
    total_employees: int = Field(..., description="Total active employees")
    total_departments: int = Field(..., description="Total active departments")
    total_payroll: Optional[Decimal] = Field(None, description="Total payroll")
    avg_salary: Optional[Decimal] = Field(None, description="Average salary")
    avg_tenure_days: Optional[float] = Field(None, description="Average employee tenure in days")
    gender_diversity_ratio: Optional[float] = Field(
        None, description="Gender diversity ratio (closer to 1.0 is more balanced)"
    )
    turnover_rate: Optional[float] = Field(None, description="Employee turnover rate percentage")
