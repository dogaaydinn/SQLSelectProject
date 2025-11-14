-- =====================================================
-- Seed Data Script
-- Description: Insert initial reference and test data
-- Author: Enterprise Architecture Team
-- Date: 2025-11-14
-- =====================================================

BEGIN;

-- =====================================================
-- SEED ROLES
-- =====================================================
INSERT INTO roles (name, description, permissions) VALUES
('admin', 'Full system administrator', '["*"]'::jsonb),
('hr_manager', 'HR department manager', '["employees:read", "employees:write", "salaries:read", "salaries:write", "departments:read"]'::jsonb),
('department_manager', 'Department manager', '["employees:read", "departments:read", "salaries:read"]'::jsonb),
('employee', 'Regular employee', '["employees:read_own", "salaries:read_own"]'::jsonb),
('readonly', 'Read-only access', '["employees:read", "departments:read", "salaries:read"]'::jsonb),
('api_user', 'API integration user', '["api:read", "api:write"]'::jsonb)
ON CONFLICT (name) DO NOTHING;

-- =====================================================
-- SEED ADMIN USER
-- =====================================================
-- Password: Admin@123 (hashed with bcrypt)
INSERT INTO users (username, email, password_hash, first_name, last_name, is_active, is_superuser, metadata) VALUES
('admin', 'admin@sqlselect.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5yvX7fJKOZ4Ry', 'System', 'Administrator', true, true, '{"created_by": "system"}'::jsonb),
('hr_manager', 'hr@sqlselect.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5yvX7fJKOZ4Ry', 'HR', 'Manager', true, false, '{"department": "Human Resources"}'::jsonb),
('api_service', 'api@sqlselect.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5yvX7fJKOZ4Ry', 'API', 'Service', true, false, '{"service": true}'::jsonb)
ON CONFLICT (username) DO NOTHING;

-- =====================================================
-- ASSIGN ROLES TO USERS
-- =====================================================
INSERT INTO user_roles (user_id, role_id, granted_by)
SELECT u.id, r.id, 1
FROM users u, roles r
WHERE (u.username = 'admin' AND r.name = 'admin')
   OR (u.username = 'hr_manager' AND r.name = 'hr_manager')
   OR (u.username = 'api_service' AND r.name = 'api_user')
ON CONFLICT DO NOTHING;

-- =====================================================
-- UPDATE EXISTING DEPARTMENTS WITH ADDITIONAL DATA
-- =====================================================
UPDATE departments SET
    description = CASE dept_name
        WHEN 'Marketing' THEN 'Responsible for brand management, advertising, and market research'
        WHEN 'Finance' THEN 'Manages financial planning, accounting, and reporting'
        WHEN 'Human Resources' THEN 'Handles recruitment, employee relations, and benefits administration'
        WHEN 'Production' THEN 'Oversees manufacturing and production operations'
        WHEN 'Development' THEN 'Software and product development team'
        WHEN 'Quality Management' THEN 'Ensures product quality and compliance'
        WHEN 'Sales' THEN 'Drives revenue through customer acquisition and retention'
        WHEN 'Research' THEN 'Conducts research and development for new products'
        WHEN 'Customer Service' THEN 'Provides customer support and satisfaction'
        ELSE 'Department description pending'
    END,
    location = CASE dept_name
        WHEN 'Marketing' THEN 'New York, NY'
        WHEN 'Finance' THEN 'New York, NY'
        WHEN 'Human Resources' THEN 'Chicago, IL'
        WHEN 'Production' THEN 'Detroit, MI'
        WHEN 'Development' THEN 'San Francisco, CA'
        WHEN 'Quality Management' THEN 'Austin, TX'
        WHEN 'Sales' THEN 'Los Angeles, CA'
        WHEN 'Research' THEN 'Boston, MA'
        WHEN 'Customer Service' THEN 'Phoenix, AZ'
        ELSE 'Remote'
    END,
    budget = CASE dept_name
        WHEN 'Marketing' THEN 2500000.00
        WHEN 'Finance' THEN 1800000.00
        WHEN 'Human Resources' THEN 1200000.00
        WHEN 'Production' THEN 5000000.00
        WHEN 'Development' THEN 8000000.00
        WHEN 'Quality Management' THEN 1500000.00
        WHEN 'Sales' THEN 3500000.00
        WHEN 'Research' THEN 6000000.00
        WHEN 'Customer Service' THEN 2000000.00
        ELSE 1000000.00
    END,
    is_active = true,
    metadata = jsonb_build_object(
        'headcount_limit', 100,
        'cost_center', 'CC-' || dept_no,
        'region', CASE dept_name
            WHEN 'Marketing' THEN 'Northeast'
            WHEN 'Finance' THEN 'Northeast'
            WHEN 'Human Resources' THEN 'Midwest'
            WHEN 'Production' THEN 'Midwest'
            WHEN 'Development' THEN 'West'
            WHEN 'Quality Management' THEN 'South'
            WHEN 'Sales' THEN 'West'
            WHEN 'Research' THEN 'Northeast'
            WHEN 'Customer Service' THEN 'Southwest'
            ELSE 'Unknown'
        END
    )
WHERE is_deleted = FALSE;

-- =====================================================
-- ENHANCE EMPLOYEE DATA (Sample enrichment)
-- =====================================================

-- Update email addresses for employees (first 100)
UPDATE employees e
SET
    email = LOWER(first_name || '.' || last_name || '@sqlselect.com'),
    phone = '+1-555-' || LPAD((1000 + emp_no % 9000)::TEXT, 4, '0'),
    country = 'USA',
    metadata = jsonb_build_object(
        'employee_type', CASE WHEN emp_no % 10 < 7 THEN 'Full-Time' WHEN emp_no % 10 < 9 THEN 'Part-Time' ELSE 'Contract' END,
        'work_location', CASE WHEN emp_no % 3 = 0 THEN 'Remote' WHEN emp_no % 3 = 1 THEN 'Hybrid' ELSE 'On-Site' END,
        'manager_id', CASE WHEN emp_no % 50 != 0 THEN (emp_no - (emp_no % 50) + 1) ELSE NULL END
    )
WHERE emp_no BETWEEN 10001 AND 10100
    AND is_deleted = FALSE;

-- =====================================================
-- CREATE SAMPLE TITLES FOR EMPLOYEES
-- =====================================================
INSERT INTO titles (emp_no, title, from_date, to_date)
SELECT
    e.emp_no,
    CASE
        WHEN e.emp_no % 50 = 1 THEN 'Senior Manager'
        WHEN e.emp_no % 20 = 0 THEN 'Manager'
        WHEN e.emp_no % 10 < 3 THEN 'Senior Engineer'
        WHEN e.emp_no % 10 < 6 THEN 'Engineer'
        WHEN e.emp_no % 10 < 8 THEN 'Analyst'
        ELSE 'Associate'
    END as title,
    e.hire_date as from_date,
    '9999-12-31'::DATE as to_date
FROM employees e
WHERE e.emp_no BETWEEN 10001 AND 10200
    AND NOT EXISTS (
        SELECT 1 FROM titles t
        WHERE t.emp_no = e.emp_no AND t.to_date = '9999-12-31'
    );

-- =====================================================
-- INITIALIZE QUERY CACHE WITH COMMON QUERIES
-- =====================================================
INSERT INTO query_cache (query_hash, query_text, result_hash, execution_time, rows_returned) VALUES
(MD5('SELECT COUNT(*) FROM employees WHERE status = ''Active'''), 'SELECT COUNT(*) FROM employees WHERE status = ''Active''', MD5('result1'), 15, 1),
(MD5('SELECT * FROM v_current_employees LIMIT 100'), 'SELECT * FROM v_current_employees LIMIT 100', MD5('result2'), 45, 100),
(MD5('SELECT dept_no, dept_name, employee_count FROM v_department_employees'), 'SELECT dept_no, dept_name, employee_count FROM v_department_employees', MD5('result3'), 30, 9)
ON CONFLICT (query_hash) DO NOTHING;

-- =====================================================
-- CREATE SAMPLE PERFORMANCE METRICS
-- =====================================================
INSERT INTO performance_metrics (metric_name, metric_value, metric_unit, endpoint, method, response_time)
SELECT
    'api_response_time',
    (random() * 100 + 10)::DECIMAL(15,4),
    'ms',
    '/api/v1/employees',
    'GET',
    (random() * 100 + 10)::INTEGER
FROM generate_series(1, 100);

COMMIT;

-- =====================================================
-- VERIFY DATA INTEGRITY
-- =====================================================
SELECT 'Roles created: ' || COUNT(*) FROM roles;
SELECT 'Users created: ' || COUNT(*) FROM users;
SELECT 'Departments updated: ' || COUNT(*) FROM departments WHERE description IS NOT NULL;
SELECT 'Employees with emails: ' || COUNT(*) FROM employees WHERE email IS NOT NULL;
SELECT 'Titles created: ' || COUNT(*) FROM titles;

-- =====================================================
-- INITIAL STATISTICS UPDATE
-- =====================================================
ANALYZE employees;
ANALYZE departments;
ANALYZE dept_emp;
ANALYZE salaries;
ANALYZE titles;
ANALYZE users;
ANALYZE roles;
