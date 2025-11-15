# API Documentation - Employee Management System

> **Version**: 1.0.0
> **Base URL**: `http://localhost:8000/api/v1`
> **Environment**: Production-Ready

---

## Table of Contents

1. [Authentication](#authentication)
2. [Employees](#employees)
3. [Departments](#departments)
4. [Salaries](#salaries)
5. [Analytics](#analytics)
6. [Health Checks](#health-checks)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)
9. [Security](#security)

---

## Authentication

All authenticated endpoints require a JWT token in the `Authorization` header:
```
Authorization: Bearer <your-jwt-token>
```

### POST /auth/register
Register a new user account.

**Request Body:**
```json
{
  "username": "johndoe",
  "email": "john.doe@company.com",
  "password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john.doe@company.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "is_superuser": false,
  "roles": ["user"]
}
```

### POST /auth/login
Login and receive access tokens.

**Request Body:**
```json
{
  "username": "johndoe",
  "password": "SecurePassword123!"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Security Features:**
- Account lockout after 5 failed attempts (30 minutes)
- Passwords hashed with bcrypt
- JWT tokens with expiration

### POST /auth/refresh
Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### GET /auth/me
Get current user information (requires authentication).

**Response:** `200 OK`
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john.doe@company.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "is_superuser": false,
  "roles": ["user"]
}
```

---

## Employees

### GET /employees
List all employees with pagination and filtering.

**Query Parameters:**
- `page` (int, default: 1): Page number
- `page_size` (int, default: 20, max: 100): Items per page
- `search` (string): Search in name, email
- `status` (string): Filter by employment status (active, terminated)

**Response:** `200 OK`
```json
{
  "items": [
    {
      "emp_no": 10001,
      "birth_date": "1953-09-02",
      "first_name": "Georgi",
      "last_name": "Facello",
      "gender": "M",
      "hire_date": "1986-06-26",
      "email": "georgi.facello@company.com",
      "phone": "+1-555-0100",
      "status": "active",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1000,
  "page": 1,
  "page_size": 20,
  "total_pages": 50
}
```

**Caching:** 5 minutes

### GET /employees/{emp_no}
Get single employee by ID.

**Response:** `200 OK`
```json
{
  "emp_no": 10001,
  "birth_date": "1953-09-02",
  "first_name": "Georgi",
  "last_name": "Facello",
  "gender": "M",
  "hire_date": "1986-06-26",
  "email": "georgi.facello@company.com",
  "phone": "+1-555-0100",
  "status": "active"
}
```

**Errors:**
- `404 Not Found`: Employee not found

### POST /employees
Create new employee (requires authentication).

**Request Body:**
```json
{
  "birth_date": "1990-01-15",
  "first_name": "Jane",
  "last_name": "Smith",
  "gender": "F",
  "hire_date": "2024-01-01",
  "email": "jane.smith@company.com",
  "phone": "+1-555-0200"
}
```

**Response:** `201 Created`

**Validation:**
- Email must be unique
- Phone must be valid format
- Birth date must be in the past
- Hire date cannot be before birth date

### PUT /employees/{emp_no}
Update employee (requires authentication).

**Request Body:**
```json
{
  "email": "jane.smith.new@company.com",
  "phone": "+1-555-0201",
  "status": "active"
}
```

**Response:** `200 OK`

### DELETE /employees/{emp_no}
Soft delete employee (requires authentication).

**Response:** `204 No Content`

**Note:** This is a soft delete - data is retained with `is_deleted=true`

---

## Departments

### GET /departments
List all departments.

**Query Parameters:**
- `page` (int): Page number
- `page_size` (int): Items per page
- `active_only` (bool, default: true): Show only active departments

**Response:** `200 OK`
```json
{
  "items": [
    {
      "dept_no": "d001",
      "dept_name": "Engineering",
      "description": "Software and hardware engineering teams",
      "budget": 5000000.00,
      "location": "Building A",
      "status": "active",
      "employee_count": 150
    }
  ],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

### GET /departments/{dept_no}
Get department details.

**Response:** `200 OK` (includes employee count, budget utilization)

### GET /departments/{dept_no}/employees
Get all employees in a department.

**Query Parameters:**
- `page` (int): Page number
- `page_size` (int): Items per page

### GET /departments/{dept_no}/statistics
Get department statistics.

**Response:** `200 OK`
```json
{
  "dept_no": "d001",
  "dept_name": "Engineering",
  "total_employees": 150,
  "active_employees": 145,
  "average_salary": 85000.00,
  "total_budget": 5000000.00,
  "budget_utilized": 4250000.00,
  "budget_utilization_percent": 85.0,
  "gender_distribution": {
    "M": 90,
    "F": 60
  }
}
```

---

## Salaries

### GET /salaries
List all salaries with filters.

**Query Parameters:**
- `page` (int): Page number
- `page_size` (int): Items per page
- `emp_no` (int): Filter by employee number
- `min_salary` (decimal): Minimum salary filter
- `max_salary` (decimal): Maximum salary filter
- `current_only` (bool, default: true): Only show current salaries

**Response:** `200 OK`
```json
{
  "items": [
    {
      "id": 1,
      "emp_no": 10001,
      "salary": 85000.00,
      "from_date": "2024-01-01",
      "to_date": "9999-01-01",
      "bonus": 5000.00,
      "commission": 2000.00,
      "currency": "USD",
      "is_current": true
    }
  ],
  "total": 500
}
```

### GET /employees/{emp_no}/salaries
Get salary history for an employee.

### GET /employees/{emp_no}/salary/current
Get current salary for an employee.

**Response:** `200 OK`
```json
{
  "emp_no": 10001,
  "salary": 85000.00,
  "bonus": 5000.00,
  "commission": 2000.00,
  "total_compensation": 92000.00,
  "from_date": "2024-01-01",
  "currency": "USD"
}
```

### POST /salaries
Create new salary record (requires authentication).

**Request Body:**
```json
{
  "emp_no": 10001,
  "salary": 90000.00,
  "from_date": "2024-07-01",
  "to_date": "9999-01-01",
  "bonus": 6000.00,
  "commission": 2500.00
}
```

**Validation:**
- No overlapping salary periods for same employee
- Salary increase must not exceed 30% (business rule)
- from_date must be before to_date

---

## Analytics

### GET /analytics/salary/statistics
Get salary statistics.

**Response:** `200 OK`
```json
{
  "total_employees": 1000,
  "average_salary": 75000.00,
  "median_salary": 72000.00,
  "min_salary": 35000.00,
  "max_salary": 250000.00,
  "salary_percentiles": {
    "p25": 55000.00,
    "p50": 72000.00,
    "p75": 95000.00,
    "p90": 125000.00
  }
}
```

### GET /analytics/departments/distribution
Get department employee distribution.

### GET /analytics/gender/diversity
Get gender diversity metrics.

**Response:** `200 OK`
```json
{
  "total_employees": 1000,
  "gender_distribution": {
    "M": 600,
    "F": 400
  },
  "gender_percentage": {
    "M": 60.0,
    "F": 40.0
  },
  "diversity_score": 0.48
}
```

### GET /analytics/hiring/trends
Get hiring trends over time.

**Query Parameters:**
- `start_date` (date): Start date for analysis
- `end_date` (date): End date for analysis
- `granularity` (string): "day", "month", "year"

---

## Health Checks

### GET /health
Basic health check.

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "service": "Employee Management System API",
  "version": "1.0.0",
  "environment": "production"
}
```

### GET /api/v1/health/detailed
Detailed health check with component status.

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "latency_ms": 5.2
    },
    "cache": {
      "status": "healthy",
      "latency_ms": 1.1,
      "memory_usage_mb": 245
    },
    "external_services": {
      "analytics": "healthy",
      "graphql": "healthy"
    }
  }
}
```

### GET /api/v1/health/liveness
Kubernetes liveness probe (basic check).

### GET /api/v1/health/readiness
Kubernetes readiness probe (checks all dependencies).

---

## Error Handling

All errors follow a consistent format:

```json
{
  "error": "Error Type",
  "detail": "Detailed error message",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing or invalid authentication |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource already exists |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Validation Errors

```json
{
  "error": "Validation Error",
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ],
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Rate Limiting

All endpoints are rate-limited:

| Endpoint | Limit |
|----------|-------|
| `/auth/login` | 5 requests/minute |
| `/auth/register` | 3 requests/hour |
| Write operations (POST/PUT/DELETE) | 30 requests/minute |
| Read operations (GET) | 100 requests/minute |
| Admin endpoints | 1000 requests/minute |

**Headers:**
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Timestamp when limit resets

**Error Response (429):**
```json
{
  "error": "Rate limit exceeded",
  "detail": "Too many requests. Please try again later.",
  "retry_after": 60
}
```

---

## Security

### HTTPS Required
All production endpoints must use HTTPS.

### Headers
All responses include security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`

### Input Validation
- All inputs are validated using Pydantic schemas
- SQL injection prevention via parameterized queries
- XSS prevention via output encoding

### Authentication
- JWT tokens with expiration
- Refresh token rotation
- Account lockout after failed attempts
- Password complexity requirements (min 8 chars)

### Authorization
- Role-based access control (RBAC)
- Permission-based access
- API key authentication for service-to-service

---

## Interactive Documentation

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **OpenAPI Schema**: http://localhost:8000/api/v1/openapi.json

---

## Support

For issues or questions:
- **GitHub Issues**: https://github.com/dogaaydinn/SQLSelectProject/issues
- **Email**: support@company.com

---

**Last Updated**: 2025-11-15
**API Version**: 1.0.0
**Status**: Production-Ready ✅
