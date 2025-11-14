-- =====================================================
-- Migration V3: Views and Materialized Views
-- Description: Create optimized views for common queries
-- Author: Enterprise Architecture Team
-- Date: 2025-11-14
-- =====================================================

-- =====================================================
-- STANDARD VIEWS
-- =====================================================

-- Current employee summary view
CREATE OR REPLACE VIEW v_current_employees AS
SELECT
    e.emp_no,
    e.uuid,
    e.first_name,
    e.last_name,
    e.first_name || ' ' || e.last_name AS full_name,
    e.gender,
    e.birth_date,
    calculate_age(e.birth_date) AS age,
    e.hire_date,
    calculate_years_of_service(e.hire_date) AS years_of_service,
    e.email,
    e.phone,
    e.status,
    d.dept_no,
    d.dept_name,
    s.salary AS current_salary,
    s.currency,
    t.title AS current_title,
    e.created_at,
    e.updated_at
FROM employees e
LEFT JOIN dept_emp de ON e.emp_no = de.emp_no
    AND de.to_date = '9999-12-31'
    AND de.is_deleted = FALSE
LEFT JOIN departments d ON de.dept_no = d.dept_no
    AND d.is_deleted = FALSE
LEFT JOIN salaries s ON e.emp_no = s.emp_no
    AND s.to_date = '9999-12-31'
    AND s.is_deleted = FALSE
LEFT JOIN titles t ON e.emp_no = t.emp_no
    AND t.to_date = '9999-12-31'
    AND t.is_deleted = FALSE
WHERE e.is_deleted = FALSE
    AND e.status = 'Active';

-- Department employee count view
CREATE OR REPLACE VIEW v_department_employees AS
SELECT
    d.dept_no,
    d.dept_name,
    d.description,
    d.location,
    COUNT(DISTINCT de.emp_no) AS employee_count,
    COUNT(DISTINCT CASE WHEN e.gender = 'M' THEN de.emp_no END) AS male_count,
    COUNT(DISTINCT CASE WHEN e.gender = 'F' THEN de.emp_no END) AS female_count,
    ROUND(AVG(s.salary), 2) AS avg_salary,
    MIN(s.salary) AS min_salary,
    MAX(s.salary) AS max_salary,
    ROUND(SUM(s.salary), 2) AS total_payroll
FROM departments d
LEFT JOIN dept_emp de ON d.dept_no = de.dept_no
    AND de.to_date = '9999-12-31'
    AND de.is_deleted = FALSE
LEFT JOIN employees e ON de.emp_no = e.emp_no
    AND e.is_deleted = FALSE
    AND e.status = 'Active'
LEFT JOIN salaries s ON de.emp_no = s.emp_no
    AND s.to_date = '9999-12-31'
    AND s.is_deleted = FALSE
WHERE d.is_deleted = FALSE
GROUP BY d.dept_no, d.dept_name, d.description, d.location;

-- Salary history view with comparisons
CREATE OR REPLACE VIEW v_salary_history AS
SELECT
    s.emp_no,
    e.first_name,
    e.last_name,
    s.salary,
    s.currency,
    s.from_date,
    s.to_date,
    s.bonus,
    s.commission,
    s.salary + COALESCE(s.bonus, 0) + COALESCE(s.commission, 0) AS total_compensation,
    LAG(s.salary) OVER (PARTITION BY s.emp_no ORDER BY s.from_date) AS previous_salary,
    ROUND(
        ((s.salary - LAG(s.salary) OVER (PARTITION BY s.emp_no ORDER BY s.from_date))
        / NULLIF(LAG(s.salary) OVER (PARTITION BY s.emp_no ORDER BY s.from_date), 0)) * 100,
        2
    ) AS salary_increase_percentage,
    ROW_NUMBER() OVER (PARTITION BY s.emp_no ORDER BY s.from_date DESC) AS salary_rank
FROM salaries s
INNER JOIN employees e ON s.emp_no = e.emp_no
WHERE s.is_deleted = FALSE;

-- Employee career path view
CREATE OR REPLACE VIEW v_employee_career_path AS
SELECT
    e.emp_no,
    e.first_name || ' ' || e.last_name AS full_name,
    t.title,
    t.from_date AS title_start_date,
    t.to_date AS title_end_date,
    d.dept_name,
    de.from_date AS dept_start_date,
    de.to_date AS dept_end_date,
    s.salary,
    CASE
        WHEN t.to_date = '9999-12-31' THEN TRUE
        ELSE FALSE
    END AS is_current
FROM employees e
LEFT JOIN titles t ON e.emp_no = t.emp_no AND t.is_deleted = FALSE
LEFT JOIN dept_emp de ON e.emp_no = de.emp_no
    AND de.from_date <= t.from_date
    AND de.to_date >= t.from_date
    AND de.is_deleted = FALSE
LEFT JOIN departments d ON de.dept_no = d.dept_no
LEFT JOIN salaries s ON e.emp_no = s.emp_no
    AND s.from_date <= t.from_date
    AND s.to_date >= t.from_date
    AND s.is_deleted = FALSE
WHERE e.is_deleted = FALSE
ORDER BY e.emp_no, t.from_date DESC;

-- Active assignments view
CREATE OR REPLACE VIEW v_active_assignments AS
SELECT
    de.emp_no,
    e.first_name || ' ' || e.last_name AS employee_name,
    de.dept_no,
    d.dept_name,
    de.from_date,
    de.is_primary,
    de.title,
    s.salary AS current_salary,
    e.hire_date,
    calculate_years_of_service(e.hire_date) AS tenure_years
FROM dept_emp de
INNER JOIN employees e ON de.emp_no = e.emp_no
    AND e.is_deleted = FALSE
    AND e.status = 'Active'
INNER JOIN departments d ON de.dept_no = d.dept_no
    AND d.is_deleted = FALSE
LEFT JOIN salaries s ON de.emp_no = s.emp_no
    AND s.to_date = '9999-12-31'
    AND s.is_deleted = FALSE
WHERE de.to_date = '9999-12-31'
    AND de.is_deleted = FALSE;

-- Salary percentile view
CREATE OR REPLACE VIEW v_salary_percentiles AS
WITH salary_data AS (
    SELECT
        s.emp_no,
        e.first_name || ' ' || e.last_name AS employee_name,
        s.salary,
        d.dept_no,
        d.dept_name,
        NTILE(100) OVER (ORDER BY s.salary) AS overall_percentile,
        NTILE(100) OVER (PARTITION BY d.dept_no ORDER BY s.salary) AS dept_percentile
    FROM salaries s
    INNER JOIN employees e ON s.emp_no = e.emp_no
        AND e.is_deleted = FALSE
        AND e.status = 'Active'
    LEFT JOIN dept_emp de ON s.emp_no = de.emp_no
        AND de.to_date = '9999-12-31'
        AND de.is_deleted = FALSE
    LEFT JOIN departments d ON de.dept_no = d.dept_no
    WHERE s.to_date = '9999-12-31'
        AND s.is_deleted = FALSE
)
SELECT
    emp_no,
    employee_name,
    salary,
    dept_no,
    dept_name,
    overall_percentile,
    dept_percentile,
    CASE
        WHEN overall_percentile >= 90 THEN 'Top 10%'
        WHEN overall_percentile >= 75 THEN 'Top 25%'
        WHEN overall_percentile >= 50 THEN 'Top 50%'
        ELSE 'Bottom 50%'
    END AS salary_tier
FROM salary_data;

-- Employee demographics view
CREATE OR REPLACE VIEW v_employee_demographics AS
SELECT
    gender,
    COUNT(*) AS total_count,
    ROUND(AVG(calculate_age(birth_date)), 1) AS avg_age,
    ROUND(AVG(calculate_years_of_service(hire_date)), 1) AS avg_tenure,
    ROUND(AVG(s.salary), 2) AS avg_salary,
    MIN(hire_date) AS earliest_hire_date,
    MAX(hire_date) AS latest_hire_date
FROM employees e
LEFT JOIN salaries s ON e.emp_no = s.emp_no
    AND s.to_date = '9999-12-31'
    AND s.is_deleted = FALSE
WHERE e.is_deleted = FALSE
    AND e.status = 'Active'
GROUP BY gender;

-- =====================================================
-- MATERIALIZED VIEWS (For Performance)
-- =====================================================

-- Materialized view: Employee summary (refreshed hourly)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_employee_summary AS
SELECT
    e.emp_no,
    e.uuid,
    e.first_name,
    e.last_name,
    e.email,
    e.gender,
    e.birth_date,
    e.hire_date,
    e.status,
    d.dept_no,
    d.dept_name,
    s.salary,
    t.title,
    calculate_age(e.birth_date) AS age,
    calculate_years_of_service(e.hire_date) AS years_of_service,
    RANK() OVER (PARTITION BY d.dept_no ORDER BY s.salary DESC) AS salary_rank_in_dept,
    PERCENT_RANK() OVER (ORDER BY s.salary) AS salary_percentile,
    CURRENT_TIMESTAMP AS last_refresh
FROM employees e
LEFT JOIN dept_emp de ON e.emp_no = de.emp_no
    AND de.to_date = '9999-12-31'
    AND de.is_deleted = FALSE
LEFT JOIN departments d ON de.dept_no = d.dept_no
LEFT JOIN salaries s ON e.emp_no = s.emp_no
    AND s.to_date = '9999-12-31'
    AND s.is_deleted = FALSE
LEFT JOIN titles t ON e.emp_no = t.emp_no
    AND t.to_date = '9999-12-31'
    AND t.is_deleted = FALSE
WHERE e.is_deleted = FALSE;

CREATE UNIQUE INDEX idx_mv_employee_summary_emp_no ON mv_employee_summary(emp_no);
CREATE INDEX idx_mv_employee_summary_dept ON mv_employee_summary(dept_no);
CREATE INDEX idx_mv_employee_summary_salary ON mv_employee_summary(salary);

-- Materialized view: Department summary (refreshed daily)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_department_summary AS
SELECT
    d.dept_no,
    d.dept_name,
    d.location,
    d.budget,
    COUNT(DISTINCT de.emp_no) AS total_employees,
    COUNT(DISTINCT CASE WHEN e.gender = 'M' THEN de.emp_no END) AS male_employees,
    COUNT(DISTINCT CASE WHEN e.gender = 'F' THEN de.emp_no END) AS female_employees,
    ROUND(AVG(s.salary), 2) AS avg_salary,
    ROUND(STDDEV(s.salary), 2) AS salary_stddev,
    MIN(s.salary) AS min_salary,
    MAX(s.salary) AS max_salary,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY s.salary) AS median_salary,
    ROUND(SUM(s.salary), 2) AS total_payroll,
    ROUND(AVG(calculate_years_of_service(e.hire_date)), 2) AS avg_tenure,
    CURRENT_TIMESTAMP AS last_refresh
FROM departments d
LEFT JOIN dept_emp de ON d.dept_no = de.dept_no
    AND de.to_date = '9999-12-31'
    AND de.is_deleted = FALSE
LEFT JOIN employees e ON de.emp_no = e.emp_no
    AND e.is_deleted = FALSE
    AND e.status = 'Active'
LEFT JOIN salaries s ON de.emp_no = s.emp_no
    AND s.to_date = '9999-12-31'
    AND s.is_deleted = FALSE
WHERE d.is_deleted = FALSE
GROUP BY d.dept_no, d.dept_name, d.location, d.budget;

CREATE UNIQUE INDEX idx_mv_department_summary_dept_no ON mv_department_summary(dept_no);

-- Materialized view: Salary trends (refreshed daily)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_salary_trends AS
WITH yearly_salaries AS (
    SELECT
        EXTRACT(YEAR FROM s.from_date) AS year,
        d.dept_no,
        d.dept_name,
        COUNT(DISTINCT s.emp_no) AS employee_count,
        ROUND(AVG(s.salary), 2) AS avg_salary,
        ROUND(MIN(s.salary), 2) AS min_salary,
        ROUND(MAX(s.salary), 2) AS max_salary,
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY s.salary), 2) AS median_salary
    FROM salaries s
    INNER JOIN dept_emp de ON s.emp_no = de.emp_no
        AND de.is_deleted = FALSE
    INNER JOIN departments d ON de.dept_no = d.dept_no
    WHERE s.is_deleted = FALSE
    GROUP BY year, d.dept_no, d.dept_name
)
SELECT
    year,
    dept_no,
    dept_name,
    employee_count,
    avg_salary,
    min_salary,
    max_salary,
    median_salary,
    LAG(avg_salary) OVER (PARTITION BY dept_no ORDER BY year) AS prev_year_avg_salary,
    ROUND(
        ((avg_salary - LAG(avg_salary) OVER (PARTITION BY dept_no ORDER BY year))
        / NULLIF(LAG(avg_salary) OVER (PARTITION BY dept_no ORDER BY year), 0)) * 100,
        2
    ) AS yoy_growth_percentage,
    CURRENT_TIMESTAMP AS last_refresh
FROM yearly_salaries
ORDER BY year DESC, dept_no;

CREATE INDEX idx_mv_salary_trends_year ON mv_salary_trends(year);
CREATE INDEX idx_mv_salary_trends_dept ON mv_salary_trends(dept_no);

-- Materialized view: High performers (refreshed weekly)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_high_performers AS
WITH performance_metrics AS (
    SELECT
        e.emp_no,
        e.first_name || ' ' || e.last_name AS employee_name,
        d.dept_name,
        s.salary,
        calculate_years_of_service(e.hire_date) AS tenure,
        COUNT(DISTINCT sh.id) AS salary_increases,
        ROUND(
            ((s.salary - MIN(sh.salary)) / NULLIF(MIN(sh.salary), 0)) * 100,
            2
        ) AS total_salary_growth_pct
    FROM employees e
    INNER JOIN salaries s ON e.emp_no = s.emp_no
        AND s.to_date = '9999-12-31'
        AND s.is_deleted = FALSE
    INNER JOIN dept_emp de ON e.emp_no = de.emp_no
        AND de.to_date = '9999-12-31'
        AND de.is_deleted = FALSE
    INNER JOIN departments d ON de.dept_no = d.dept_no
    LEFT JOIN salaries sh ON e.emp_no = sh.emp_no
        AND sh.is_deleted = FALSE
    WHERE e.is_deleted = FALSE
        AND e.status = 'Active'
    GROUP BY e.emp_no, employee_name, d.dept_name, s.salary, tenure
)
SELECT
    emp_no,
    employee_name,
    dept_name,
    salary,
    tenure,
    salary_increases,
    total_salary_growth_pct,
    NTILE(10) OVER (ORDER BY total_salary_growth_pct DESC) AS performance_decile,
    CURRENT_TIMESTAMP AS last_refresh
FROM performance_metrics
WHERE tenure >= 1
    AND salary_increases >= 2;

CREATE UNIQUE INDEX idx_mv_high_performers_emp_no ON mv_high_performers(emp_no);
CREATE INDEX idx_mv_high_performers_dept ON mv_high_performers(dept_name);

-- =====================================================
-- SEARCH VIEWS
-- =====================================================

-- Full-text search view for employees
CREATE OR REPLACE VIEW v_employee_search AS
SELECT
    e.emp_no,
    e.uuid,
    e.first_name || ' ' || e.last_name AS full_name,
    e.email,
    d.dept_name,
    t.title,
    to_tsvector('english',
        COALESCE(e.first_name, '') || ' ' ||
        COALESCE(e.last_name, '') || ' ' ||
        COALESCE(e.email, '') || ' ' ||
        COALESCE(d.dept_name, '') || ' ' ||
        COALESCE(t.title, '')
    ) AS search_vector
FROM employees e
LEFT JOIN dept_emp de ON e.emp_no = de.emp_no
    AND de.to_date = '9999-12-31'
    AND de.is_deleted = FALSE
LEFT JOIN departments d ON de.dept_no = d.dept_no
LEFT JOIN titles t ON e.emp_no = t.emp_no
    AND t.to_date = '9999-12-31'
    AND t.is_deleted = FALSE
WHERE e.is_deleted = FALSE;

-- =====================================================
-- COMMENTS
-- =====================================================
COMMENT ON VIEW v_current_employees IS 'Current active employees with all related information';
COMMENT ON VIEW v_department_employees IS 'Department statistics and employee counts';
COMMENT ON VIEW v_salary_history IS 'Complete salary history with growth calculations';
COMMENT ON VIEW v_employee_career_path IS 'Employee career progression across titles and departments';
COMMENT ON VIEW v_active_assignments IS 'Current department assignments for active employees';
COMMENT ON VIEW v_salary_percentiles IS 'Salary distribution and percentiles';
COMMENT ON VIEW v_employee_demographics IS 'Demographic statistics for active employees';
COMMENT ON VIEW v_employee_search IS 'Full-text search view for employees';

COMMENT ON MATERIALIZED VIEW mv_employee_summary IS 'Cached employee summary - refresh hourly';
COMMENT ON MATERIALIZED VIEW mv_department_summary IS 'Cached department statistics - refresh daily';
COMMENT ON MATERIALIZED VIEW mv_salary_trends IS 'Historical salary trends - refresh daily';
COMMENT ON MATERIALIZED VIEW mv_high_performers IS 'High-performing employees - refresh weekly';
