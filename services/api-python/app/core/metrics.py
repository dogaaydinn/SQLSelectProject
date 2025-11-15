"""
Custom Prometheus Metrics
Business KPI metrics for monitoring and alerting
"""

from prometheus_client import Counter, Gauge, Histogram, Info
from app.core.logging import logger

# ============================================
# BUSINESS KPI METRICS
# ============================================

# Employee Metrics
employee_created_total = Counter(
    "employee_created_total",
    "Total number of employees created",
    ["status", "department"],
)

employee_updated_total = Counter(
    "employee_updated_total",
    "Total number of employees updated",
    ["status"],
)

employee_deleted_total = Counter(
    "employee_deleted_total",
    "Total number of employees deleted",
    ["soft_delete"],
)

employee_count_by_status = Gauge(
    "employee_count_by_status",
    "Current number of employees by status",
    ["status"],
)

employee_count_by_department = Gauge(
    "employee_count_by_department",
    "Current number of employees by department",
    ["department", "department_name"],
)

# Salary Metrics
salary_created_total = Counter(
    "salary_created_total",
    "Total number of salary records created",
)

salary_adjusted_total = Counter(
    "salary_adjusted_total",
    "Total number of salary adjustments",
    ["change_type"],  # increase, decrease, no_change
)

salary_adjustment_percent = Histogram(
    "salary_adjustment_percent",
    "Salary adjustment percentage distribution",
    buckets=[-50, -20, -10, -5, 0, 5, 10, 20, 50, 100],
)

current_salary_stats = Gauge(
    "current_salary_stats",
    "Current salary statistics",
    ["metric"],  # mean, median, min, max
)

department_avg_salary = Gauge(
    "department_avg_salary",
    "Average salary by department",
    ["department", "department_name"],
)

# Department Metrics
department_budget_utilization = Gauge(
    "department_budget_utilization",
    "Department budget utilization percentage",
    ["department", "department_name"],
)

department_budget_updated_total = Counter(
    "department_budget_updated_total",
    "Total number of budget updates",
    ["department"],
)

# Authentication & Security Metrics
login_attempts_total = Counter(
    "login_attempts_total",
    "Total login attempts",
    ["status", "user_type"],  # status: success, failed, locked
)

failed_login_by_user = Counter(
    "failed_login_by_user",
    "Failed login attempts by user",
    ["username"],
)

account_locked_total = Counter(
    "account_locked_total",
    "Total number of account lockouts",
)

active_sessions = Gauge(
    "active_sessions",
    "Current number of active sessions",
    ["user_type"],
)

# API Operation Metrics
api_operation_duration = Histogram(
    "api_operation_duration_seconds",
    "Duration of API operations",
    ["operation", "endpoint", "method"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

api_operation_errors = Counter(
    "api_operation_errors_total",
    "Total number of API operation errors",
    ["operation", "error_type"],
)

# Database Metrics
db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["query_type", "table"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

db_connection_pool_size = Gauge(
    "db_connection_pool_size",
    "Database connection pool size",
    ["status"],  # active, idle
)

db_query_errors = Counter(
    "db_query_errors_total",
    "Total number of database query errors",
    ["error_type"],
)

# Cache Metrics
cache_operations_total = Counter(
    "cache_operations_total",
    "Total cache operations",
    ["operation", "status"],  # operation: get, set, delete; status: hit, miss, error
)

cache_hit_ratio = Gauge(
    "cache_hit_ratio",
    "Cache hit ratio percentage",
)

cache_evictions_total = Counter(
    "cache_evictions_total",
    "Total number of cache evictions",
)

# Batch Operation Metrics
batch_import_total = Counter(
    "batch_import_total",
    "Total batch import operations",
    ["entity_type", "status"],
)

batch_import_records = Histogram(
    "batch_import_records",
    "Number of records in batch import",
    ["entity_type"],
    buckets=[10, 50, 100, 500, 1000, 5000, 10000],
)

# Service Health Metrics
service_health = Gauge(
    "service_health_status",
    "Service health status (1=healthy, 0=unhealthy)",
    ["component"],
)

# Application Info
app_info = Info(
    "app",
    "Application information",
)

# ============================================
# HELPER FUNCTIONS
# ============================================

def record_employee_created(status: str, department: str = "unknown"):
    """Record employee creation."""
    employee_created_total.labels(status=status, department=department).inc()
    logger.debug(f"Metric recorded: employee_created (status={status}, dept={department})")


def record_employee_updated(status: str):
    """Record employee update."""
    employee_updated_total.labels(status=status).inc()


def record_employee_deleted(soft_delete: bool):
    """Record employee deletion."""
    employee_deleted_total.labels(soft_delete=str(soft_delete)).inc()


def record_salary_adjustment(old_salary: float, new_salary: float):
    """Record salary adjustment."""
    if old_salary > 0:
        change_percent = ((new_salary - old_salary) / old_salary) * 100
        salary_adjustment_percent.observe(change_percent)

        if new_salary > old_salary:
            change_type = "increase"
        elif new_salary < old_salary:
            change_type = "decrease"
        else:
            change_type = "no_change"

        salary_adjusted_total.labels(change_type=change_type).inc()


def record_login_attempt(status: str, user_type: str = "user", username: str = None):
    """Record login attempt."""
    login_attempts_total.labels(status=status, user_type=user_type).inc()

    if status == "failed" and username:
        failed_login_by_user.labels(username=username).inc()

    if status == "locked":
        account_locked_total.inc()


def update_salary_statistics(mean: float, median: float, min_val: float, max_val: float):
    """Update current salary statistics."""
    current_salary_stats.labels(metric="mean").set(mean)
    current_salary_stats.labels(metric="median").set(median)
    current_salary_stats.labels(metric="min").set(min_val)
    current_salary_stats.labels(metric="max").set(max_val)


def update_employee_counts(status_counts: dict):
    """Update employee counts by status."""
    for status, count in status_counts.items():
        employee_count_by_status.labels(status=status).set(count)


def update_department_metrics(department_stats: list):
    """Update department-level metrics."""
    for dept in department_stats:
        dept_no = dept.get("dept_no")
        dept_name = dept.get("dept_name", "unknown")
        employee_count = dept.get("employee_count", 0)
        avg_salary = dept.get("avg_salary", 0.0)

        employee_count_by_department.labels(
            department=dept_no,
            department_name=dept_name,
        ).set(employee_count)

        department_avg_salary.labels(
            department=dept_no,
            department_name=dept_name,
        ).set(avg_salary)


def record_cache_operation(operation: str, status: str):
    """Record cache operation."""
    cache_operations_total.labels(operation=operation, status=status).inc()


def update_cache_hit_ratio(hits: int, total: int):
    """Update cache hit ratio."""
    if total > 0:
        ratio = (hits / total) * 100
        cache_hit_ratio.set(ratio)


def record_api_error(operation: str, error_type: str):
    """Record API operation error."""
    api_operation_errors.labels(operation=operation, error_type=error_type).inc()


def record_db_query_error(error_type: str):
    """Record database query error."""
    db_query_errors.labels(error_type=error_type).inc()


def update_service_health(component: str, is_healthy: bool):
    """Update service health status."""
    service_health.labels(component=component).set(1 if is_healthy else 0)


def initialize_app_info(app_name: str, version: str, environment: str):
    """Initialize application info metric."""
    app_info.info({
        "app_name": app_name,
        "version": version,
        "environment": environment,
    })
    logger.info(f"Application info metric initialized: {app_name} v{version} ({environment})")


# Initialize app info on module import
try:
    from app.core.config import settings
    initialize_app_info(
        settings.PROJECT_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
    )
except Exception as e:
    logger.warning(f"Failed to initialize app info: {e}")
