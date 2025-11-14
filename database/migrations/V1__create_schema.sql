-- =====================================================
-- Migration V1: Initial Schema Creation
-- Description: Create base tables with optimized structure
-- Author: Enterprise Architecture Team
-- Date: 2025-11-14
-- =====================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- Create custom types
CREATE TYPE gender_type AS ENUM ('M', 'F', 'Other', 'PreferNotToSay');
CREATE TYPE employment_status AS ENUM ('Active', 'Terminated', 'OnLeave', 'Suspended');
CREATE TYPE audit_action AS ENUM ('INSERT', 'UPDATE', 'DELETE');

-- =====================================================
-- EMPLOYEES TABLE (Enhanced)
-- =====================================================
CREATE TABLE IF NOT EXISTS employees (
    emp_no          SERIAL          PRIMARY KEY,
    uuid            UUID            NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    birth_date      DATE            NOT NULL CHECK (birth_date >= '1930-01-01' AND birth_date <= CURRENT_DATE),
    first_name      VARCHAR(50)     NOT NULL CHECK (LENGTH(TRIM(first_name)) > 0),
    last_name       VARCHAR(50)     NOT NULL CHECK (LENGTH(TRIM(last_name)) > 0),
    middle_name     VARCHAR(50),
    gender          gender_type     NOT NULL DEFAULT 'PreferNotToSay',
    hire_date       DATE            NOT NULL CHECK (hire_date >= '1980-01-01'),
    termination_date DATE           CHECK (termination_date IS NULL OR termination_date >= hire_date),
    status          employment_status NOT NULL DEFAULT 'Active',
    email           VARCHAR(255)    UNIQUE,
    phone           VARCHAR(20),
    address_line1   VARCHAR(255),
    address_line2   VARCHAR(255),
    city            VARCHAR(100),
    state           VARCHAR(100),
    country         VARCHAR(100)    DEFAULT 'USA',
    postal_code     VARCHAR(20),
    ssn_encrypted   TEXT,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by      INTEGER,
    updated_by      INTEGER,
    version         INTEGER         NOT NULL DEFAULT 1,
    is_deleted      BOOLEAN         NOT NULL DEFAULT FALSE,
    deleted_at      TIMESTAMP,
    metadata        JSONB           DEFAULT '{}'::jsonb
);

-- Add indexes for employees
CREATE INDEX idx_employees_hire_date ON employees(hire_date) WHERE is_deleted = FALSE;
CREATE INDEX idx_employees_status ON employees(status) WHERE is_deleted = FALSE;
CREATE INDEX idx_employees_last_name ON employees(last_name) WHERE is_deleted = FALSE;
CREATE INDEX idx_employees_first_name ON employees(first_name) WHERE is_deleted = FALSE;
CREATE INDEX idx_employees_full_name ON employees(last_name, first_name) WHERE is_deleted = FALSE;
CREATE INDEX idx_employees_email ON employees(email) WHERE email IS NOT NULL AND is_deleted = FALSE;
CREATE INDEX idx_employees_uuid ON employees(uuid);
CREATE INDEX idx_employees_created_at ON employees(created_at);
CREATE INDEX idx_employees_metadata ON employees USING GIN(metadata);
CREATE INDEX idx_employees_search ON employees USING GIN(
    to_tsvector('english', COALESCE(first_name, '') || ' ' || COALESCE(last_name, '') || ' ' || COALESCE(email, ''))
);

-- =====================================================
-- DEPARTMENTS TABLE (Enhanced)
-- =====================================================
CREATE TABLE IF NOT EXISTS departments (
    dept_no         CHAR(4)         PRIMARY KEY,
    uuid            UUID            NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    dept_name       VARCHAR(100)    NOT NULL UNIQUE CHECK (LENGTH(TRIM(dept_name)) > 0),
    description     TEXT,
    manager_emp_no  INTEGER,
    budget          DECIMAL(15,2),
    location        VARCHAR(255),
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by      INTEGER,
    updated_by      INTEGER,
    version         INTEGER         NOT NULL DEFAULT 1,
    is_deleted      BOOLEAN         NOT NULL DEFAULT FALSE,
    deleted_at      TIMESTAMP,
    metadata        JSONB           DEFAULT '{}'::jsonb
);

-- Add indexes for departments
CREATE INDEX idx_departments_name ON departments(dept_name) WHERE is_deleted = FALSE;
CREATE INDEX idx_departments_manager ON departments(manager_emp_no) WHERE is_deleted = FALSE;
CREATE INDEX idx_departments_active ON departments(is_active) WHERE is_deleted = FALSE;
CREATE INDEX idx_departments_uuid ON departments(uuid);
CREATE INDEX idx_departments_metadata ON departments USING GIN(metadata);

-- =====================================================
-- DEPT_EMP TABLE (Enhanced - Employee-Department Mapping)
-- =====================================================
CREATE TABLE IF NOT EXISTS dept_emp (
    id              SERIAL          PRIMARY KEY,
    uuid            UUID            NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    emp_no          INTEGER         NOT NULL,
    dept_no         CHAR(4)         NOT NULL,
    from_date       DATE            NOT NULL,
    to_date         DATE            NOT NULL DEFAULT '9999-12-31',
    is_primary      BOOLEAN         NOT NULL DEFAULT TRUE,
    title           VARCHAR(100),
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by      INTEGER,
    updated_by      INTEGER,
    version         INTEGER         NOT NULL DEFAULT 1,
    is_deleted      BOOLEAN         NOT NULL DEFAULT FALSE,
    deleted_at      TIMESTAMP,
    metadata        JSONB           DEFAULT '{}'::jsonb,
    CONSTRAINT fk_dept_emp_employee FOREIGN KEY (emp_no)
        REFERENCES employees(emp_no) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_dept_emp_department FOREIGN KEY (dept_no)
        REFERENCES departments(dept_no) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_dept_emp_dates CHECK (to_date >= from_date),
    CONSTRAINT uq_dept_emp_active UNIQUE (emp_no, dept_no, from_date)
);

-- Add indexes for dept_emp
CREATE INDEX idx_dept_emp_employee ON dept_emp(emp_no) WHERE is_deleted = FALSE;
CREATE INDEX idx_dept_emp_department ON dept_emp(dept_no) WHERE is_deleted = FALSE;
CREATE INDEX idx_dept_emp_dates ON dept_emp(from_date, to_date) WHERE is_deleted = FALSE;
CREATE INDEX idx_dept_emp_current ON dept_emp(emp_no, dept_no)
    WHERE to_date = '9999-12-31' AND is_deleted = FALSE;
CREATE INDEX idx_dept_emp_primary ON dept_emp(emp_no)
    WHERE is_primary = TRUE AND is_deleted = FALSE;
CREATE INDEX idx_dept_emp_uuid ON dept_emp(uuid);
CREATE INDEX idx_dept_emp_metadata ON dept_emp USING GIN(metadata);

-- =====================================================
-- SALARIES TABLE (Enhanced with partitioning support)
-- =====================================================
CREATE TABLE IF NOT EXISTS salaries (
    id              BIGSERIAL       PRIMARY KEY,
    uuid            UUID            NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    emp_no          INTEGER         NOT NULL,
    salary          DECIMAL(12,2)   NOT NULL CHECK (salary > 0),
    currency        CHAR(3)         NOT NULL DEFAULT 'USD',
    from_date       DATE            NOT NULL,
    to_date         DATE            NOT NULL DEFAULT '9999-12-31',
    salary_type     VARCHAR(50)     DEFAULT 'Base',
    bonus           DECIMAL(12,2)   DEFAULT 0,
    commission      DECIMAL(12,2)   DEFAULT 0,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by      INTEGER,
    updated_by      INTEGER,
    version         INTEGER         NOT NULL DEFAULT 1,
    is_deleted      BOOLEAN         NOT NULL DEFAULT FALSE,
    deleted_at      TIMESTAMP,
    metadata        JSONB           DEFAULT '{}'::jsonb,
    CONSTRAINT fk_salaries_employee FOREIGN KEY (emp_no)
        REFERENCES employees(emp_no) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_salaries_dates CHECK (to_date >= from_date),
    CONSTRAINT uq_salaries_active UNIQUE (emp_no, from_date)
);

-- Add indexes for salaries
CREATE INDEX idx_salaries_employee ON salaries(emp_no) WHERE is_deleted = FALSE;
CREATE INDEX idx_salaries_amount ON salaries(salary) WHERE is_deleted = FALSE;
CREATE INDEX idx_salaries_dates ON salaries(from_date, to_date) WHERE is_deleted = FALSE;
CREATE INDEX idx_salaries_current ON salaries(emp_no, from_date)
    WHERE to_date = '9999-12-31' AND is_deleted = FALSE;
CREATE INDEX idx_salaries_uuid ON salaries(uuid);
CREATE INDEX idx_salaries_metadata ON salaries USING GIN(metadata);
CREATE INDEX idx_salaries_salary_range ON salaries(salary)
    WHERE is_deleted = FALSE AND to_date = '9999-12-31';

-- =====================================================
-- TITLES TABLE (New - Employee Job Titles)
-- =====================================================
CREATE TABLE IF NOT EXISTS titles (
    id              SERIAL          PRIMARY KEY,
    uuid            UUID            NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    emp_no          INTEGER         NOT NULL,
    title           VARCHAR(100)    NOT NULL,
    from_date       DATE            NOT NULL,
    to_date         DATE            DEFAULT '9999-12-31',
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    version         INTEGER         NOT NULL DEFAULT 1,
    is_deleted      BOOLEAN         NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_titles_employee FOREIGN KEY (emp_no)
        REFERENCES employees(emp_no) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_titles_dates CHECK (to_date >= from_date),
    CONSTRAINT uq_titles_active UNIQUE (emp_no, from_date)
);

CREATE INDEX idx_titles_employee ON titles(emp_no) WHERE is_deleted = FALSE;
CREATE INDEX idx_titles_title ON titles(title) WHERE is_deleted = FALSE;
CREATE INDEX idx_titles_current ON titles(emp_no)
    WHERE to_date = '9999-12-31' AND is_deleted = FALSE;

-- =====================================================
-- AUDIT LOG TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL       PRIMARY KEY,
    table_name      VARCHAR(100)    NOT NULL,
    record_id       INTEGER         NOT NULL,
    action          audit_action    NOT NULL,
    old_values      JSONB,
    new_values      JSONB,
    changed_by      INTEGER,
    changed_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address      INET,
    user_agent      TEXT,
    session_id      VARCHAR(255),
    metadata        JSONB           DEFAULT '{}'::jsonb
);

-- Partition audit log by month for performance
CREATE INDEX idx_audit_log_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_log_changed_at ON audit_log(changed_at);
CREATE INDEX idx_audit_log_changed_by ON audit_log(changed_by);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_metadata ON audit_log USING GIN(metadata);

-- =====================================================
-- USERS TABLE (For Application Authentication)
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL          PRIMARY KEY,
    uuid            UUID            NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    username        VARCHAR(50)     NOT NULL UNIQUE,
    email           VARCHAR(255)    NOT NULL UNIQUE,
    password_hash   TEXT            NOT NULL,
    first_name      VARCHAR(50),
    last_name       VARCHAR(50),
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    is_superuser    BOOLEAN         NOT NULL DEFAULT FALSE,
    last_login      TIMESTAMP,
    failed_login_attempts INTEGER    DEFAULT 0,
    locked_until    TIMESTAMP,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata        JSONB           DEFAULT '{}'::jsonb
);

CREATE INDEX idx_users_username ON users(username) WHERE is_active = TRUE;
CREATE INDEX idx_users_email ON users(email) WHERE is_active = TRUE;
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_users_uuid ON users(uuid);

-- =====================================================
-- ROLES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS roles (
    id              SERIAL          PRIMARY KEY,
    name            VARCHAR(50)     NOT NULL UNIQUE,
    description     TEXT,
    permissions     JSONB           NOT NULL DEFAULT '[]'::jsonb,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- USER_ROLES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS user_roles (
    user_id         INTEGER         NOT NULL,
    role_id         INTEGER         NOT NULL,
    granted_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    granted_by      INTEGER,
    PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_user_roles_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_user_roles_role FOREIGN KEY (role_id)
        REFERENCES roles(id) ON DELETE CASCADE
);

-- =====================================================
-- API_KEYS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id              SERIAL          PRIMARY KEY,
    key_hash        TEXT            NOT NULL UNIQUE,
    user_id         INTEGER         NOT NULL,
    name            VARCHAR(100)    NOT NULL,
    scopes          JSONB           NOT NULL DEFAULT '[]'::jsonb,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    expires_at      TIMESTAMP,
    last_used_at    TIMESTAMP,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_api_keys_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_active ON api_keys(is_active) WHERE is_active = TRUE;

-- =====================================================
-- QUERY_CACHE TABLE (For ML-optimized queries)
-- =====================================================
CREATE TABLE IF NOT EXISTS query_cache (
    id              BIGSERIAL       PRIMARY KEY,
    query_hash      VARCHAR(64)     NOT NULL UNIQUE,
    query_text      TEXT            NOT NULL,
    result_hash     VARCHAR(64)     NOT NULL,
    execution_plan  JSONB,
    execution_time  INTEGER,
    rows_returned   INTEGER,
    cache_hits      INTEGER         DEFAULT 0,
    last_accessed   TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at      TIMESTAMP,
    metadata        JSONB           DEFAULT '{}'::jsonb
);

CREATE INDEX idx_query_cache_hash ON query_cache(query_hash);
CREATE INDEX idx_query_cache_accessed ON query_cache(last_accessed);
CREATE INDEX idx_query_cache_expires ON query_cache(expires_at);

-- =====================================================
-- PERFORMANCE_METRICS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS performance_metrics (
    id              BIGSERIAL       PRIMARY KEY,
    metric_name     VARCHAR(100)    NOT NULL,
    metric_value    DECIMAL(15,4)   NOT NULL,
    metric_unit     VARCHAR(20),
    query_id        BIGINT,
    endpoint        VARCHAR(255),
    method          VARCHAR(10),
    status_code     INTEGER,
    response_time   INTEGER,
    timestamp       TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata        JSONB           DEFAULT '{}'::jsonb
);

CREATE INDEX idx_performance_metrics_name ON performance_metrics(metric_name);
CREATE INDEX idx_performance_metrics_timestamp ON performance_metrics(timestamp);
CREATE INDEX idx_performance_metrics_endpoint ON performance_metrics(endpoint);

-- =====================================================
-- COMMENTS
-- =====================================================
COMMENT ON TABLE employees IS 'Employee master data with enhanced tracking and soft delete';
COMMENT ON TABLE departments IS 'Department information with hierarchical support';
COMMENT ON TABLE dept_emp IS 'Employee-department assignments with history tracking';
COMMENT ON TABLE salaries IS 'Employee salary history with bonus and commission tracking';
COMMENT ON TABLE titles IS 'Employee job title history';
COMMENT ON TABLE audit_log IS 'Comprehensive audit trail for all data changes';
COMMENT ON TABLE users IS 'Application user accounts for authentication';
COMMENT ON TABLE roles IS 'Role definitions for RBAC';
COMMENT ON TABLE user_roles IS 'User-role assignments';
COMMENT ON TABLE api_keys IS 'API key management for external integrations';
COMMENT ON TABLE query_cache IS 'Intelligent query cache for performance optimization';
COMMENT ON TABLE performance_metrics IS 'Real-time performance monitoring data';

-- =====================================================
-- GRANT PERMISSIONS
-- =====================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO postgres;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO postgres;
