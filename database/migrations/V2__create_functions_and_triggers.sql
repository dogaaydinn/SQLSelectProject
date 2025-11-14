-- =====================================================
-- Migration V2: Functions, Triggers, and Automation
-- Description: Create stored procedures, triggers, and automated workflows
-- Author: Enterprise Architecture Team
-- Date: 2025-11-14
-- =====================================================

-- =====================================================
-- UTILITY FUNCTIONS
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to prevent updates on deleted records
CREATE OR REPLACE FUNCTION prevent_deleted_record_update()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.is_deleted = TRUE THEN
        RAISE EXCEPTION 'Cannot update deleted record in table %', TG_TABLE_NAME;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to soft delete
CREATE OR REPLACE FUNCTION soft_delete()
RETURNS TRIGGER AS $$
BEGIN
    NEW.is_deleted = TRUE;
    NEW.deleted_at = CURRENT_TIMESTAMP;
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- AUDIT LOGGING FUNCTIONS
-- =====================================================

-- Generic audit log function
CREATE OR REPLACE FUNCTION audit_log_changes()
RETURNS TRIGGER AS $$
DECLARE
    old_data JSONB;
    new_data JSONB;
    record_id INTEGER;
BEGIN
    IF TG_OP = 'DELETE' THEN
        old_data = to_jsonb(OLD);
        new_data = NULL;
        record_id = OLD.emp_no;
    ELSIF TG_OP = 'UPDATE' THEN
        old_data = to_jsonb(OLD);
        new_data = to_jsonb(NEW);
        record_id = NEW.emp_no;
    ELSIF TG_OP = 'INSERT' THEN
        old_data = NULL;
        new_data = to_jsonb(NEW);
        record_id = NEW.emp_no;
    END IF;

    INSERT INTO audit_log (
        table_name,
        record_id,
        action,
        old_values,
        new_values,
        changed_at
    ) VALUES (
        TG_TABLE_NAME,
        record_id,
        TG_OP::audit_action,
        old_data,
        new_data,
        CURRENT_TIMESTAMP
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- BUSINESS LOGIC FUNCTIONS
-- =====================================================

-- Calculate employee age
CREATE OR REPLACE FUNCTION calculate_age(birth_date DATE)
RETURNS INTEGER AS $$
BEGIN
    RETURN DATE_PART('year', AGE(birth_date));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Calculate years of service
CREATE OR REPLACE FUNCTION calculate_years_of_service(hire_date DATE, end_date DATE DEFAULT CURRENT_DATE)
RETURNS DECIMAL(10,2) AS $$
BEGIN
    RETURN ROUND(DATE_PART('day', AGE(end_date, hire_date)) / 365.25, 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Get current salary for employee
CREATE OR REPLACE FUNCTION get_current_salary(emp_id INTEGER)
RETURNS DECIMAL(12,2) AS $$
DECLARE
    current_salary DECIMAL(12,2);
BEGIN
    SELECT salary INTO current_salary
    FROM salaries
    WHERE emp_no = emp_id
      AND to_date = '9999-12-31'
      AND is_deleted = FALSE
    ORDER BY from_date DESC
    LIMIT 1;

    RETURN COALESCE(current_salary, 0);
END;
$$ LANGUAGE plpgsql STABLE;

-- Get current department for employee
CREATE OR REPLACE FUNCTION get_current_department(emp_id INTEGER)
RETURNS CHAR(4) AS $$
DECLARE
    current_dept CHAR(4);
BEGIN
    SELECT dept_no INTO current_dept
    FROM dept_emp
    WHERE emp_no = emp_id
      AND to_date = '9999-12-31'
      AND is_deleted = FALSE
    ORDER BY from_date DESC
    LIMIT 1;

    RETURN current_dept;
END;
$$ LANGUAGE plpgsql STABLE;

-- Calculate department average salary
CREATE OR REPLACE FUNCTION get_department_avg_salary(dept_id CHAR(4))
RETURNS DECIMAL(12,2) AS $$
DECLARE
    avg_salary DECIMAL(12,2);
BEGIN
    SELECT AVG(s.salary) INTO avg_salary
    FROM salaries s
    INNER JOIN dept_emp de ON s.emp_no = de.emp_no
    WHERE de.dept_no = dept_id
      AND s.to_date = '9999-12-31'
      AND de.to_date = '9999-12-31'
      AND s.is_deleted = FALSE
      AND de.is_deleted = FALSE;

    RETURN COALESCE(avg_salary, 0);
END;
$$ LANGUAGE plpgsql STABLE;

-- Validate salary change (business rule: max 30% increase)
CREATE OR REPLACE FUNCTION validate_salary_change()
RETURNS TRIGGER AS $$
DECLARE
    previous_salary DECIMAL(12,2);
    increase_percentage DECIMAL(5,2);
BEGIN
    SELECT salary INTO previous_salary
    FROM salaries
    WHERE emp_no = NEW.emp_no
      AND is_deleted = FALSE
    ORDER BY from_date DESC
    LIMIT 1;

    IF previous_salary IS NOT NULL THEN
        increase_percentage = ((NEW.salary - previous_salary) / previous_salary) * 100;

        IF increase_percentage > 30 THEN
            RAISE EXCEPTION 'Salary increase of %.2f%% exceeds maximum allowed (30%%)', increase_percentage;
        END IF;

        IF NEW.salary < previous_salary * 0.5 THEN
            RAISE EXCEPTION 'Salary decrease exceeds maximum allowed (50%%)';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Auto-terminate employee when termination date is set
CREATE OR REPLACE FUNCTION auto_terminate_employee()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.termination_date IS NOT NULL AND OLD.termination_date IS NULL THEN
        NEW.status = 'Terminated';

        -- End current department assignment
        UPDATE dept_emp
        SET to_date = NEW.termination_date
        WHERE emp_no = NEW.emp_no
          AND to_date = '9999-12-31';

        -- End current salary
        UPDATE salaries
        SET to_date = NEW.termination_date
        WHERE emp_no = NEW.emp_no
          AND to_date = '9999-12-31';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Prevent overlapping department assignments
CREATE OR REPLACE FUNCTION prevent_overlapping_dept_assignments()
RETURNS TRIGGER AS $$
DECLARE
    overlap_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO overlap_count
    FROM dept_emp
    WHERE emp_no = NEW.emp_no
      AND id != COALESCE(NEW.id, -1)
      AND is_deleted = FALSE
      AND (
          (NEW.from_date BETWEEN from_date AND to_date)
          OR (NEW.to_date BETWEEN from_date AND to_date)
          OR (from_date BETWEEN NEW.from_date AND NEW.to_date)
      );

    IF overlap_count > 0 THEN
        RAISE EXCEPTION 'Department assignment dates overlap with existing assignment';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- ANALYTICS FUNCTIONS
-- =====================================================

-- Get employee count by department
CREATE OR REPLACE FUNCTION get_employee_count_by_department()
RETURNS TABLE (
    dept_no CHAR(4),
    dept_name VARCHAR(100),
    employee_count BIGINT,
    avg_salary DECIMAL(12,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.dept_no,
        d.dept_name,
        COUNT(DISTINCT de.emp_no) as employee_count,
        ROUND(AVG(s.salary), 2) as avg_salary
    FROM departments d
    LEFT JOIN dept_emp de ON d.dept_no = de.dept_no
        AND de.to_date = '9999-12-31'
        AND de.is_deleted = FALSE
    LEFT JOIN salaries s ON de.emp_no = s.emp_no
        AND s.to_date = '9999-12-31'
        AND s.is_deleted = FALSE
    WHERE d.is_deleted = FALSE
    GROUP BY d.dept_no, d.dept_name
    ORDER BY employee_count DESC;
END;
$$ LANGUAGE plpgsql STABLE;

-- Get salary statistics
CREATE OR REPLACE FUNCTION get_salary_statistics()
RETURNS TABLE (
    min_salary DECIMAL(12,2),
    max_salary DECIMAL(12,2),
    avg_salary DECIMAL(12,2),
    median_salary DECIMAL(12,2),
    total_payroll DECIMAL(15,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        MIN(salary) as min_salary,
        MAX(salary) as max_salary,
        ROUND(AVG(salary), 2) as avg_salary,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary) as median_salary,
        ROUND(SUM(salary), 2) as total_payroll
    FROM salaries
    WHERE to_date = '9999-12-31'
      AND is_deleted = FALSE;
END;
$$ LANGUAGE plpgsql STABLE;

-- Get tenure distribution
CREATE OR REPLACE FUNCTION get_tenure_distribution()
RETURNS TABLE (
    tenure_range VARCHAR(50),
    employee_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH tenure_calc AS (
        SELECT
            emp_no,
            calculate_years_of_service(hire_date) as years
        FROM employees
        WHERE status = 'Active'
          AND is_deleted = FALSE
    )
    SELECT
        CASE
            WHEN years < 1 THEN '0-1 years'
            WHEN years < 3 THEN '1-3 years'
            WHEN years < 5 THEN '3-5 years'
            WHEN years < 10 THEN '5-10 years'
            WHEN years < 15 THEN '10-15 years'
            WHEN years < 20 THEN '15-20 years'
            ELSE '20+ years'
        END as tenure_range,
        COUNT(*) as employee_count
    FROM tenure_calc
    GROUP BY tenure_range
    ORDER BY MIN(years);
END;
$$ LANGUAGE plpgsql STABLE;

-- =====================================================
-- PERFORMANCE OPTIMIZATION FUNCTIONS
-- =====================================================

-- Refresh materialized views (for caching)
CREATE OR REPLACE FUNCTION refresh_analytics_cache()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_employee_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_department_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_salary_trends;
END;
$$ LANGUAGE plpgsql;

-- Clean old audit logs (retention: 1 year)
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM audit_log
    WHERE changed_at < CURRENT_DATE - INTERVAL '1 year';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Clean expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM query_cache
    WHERE expires_at < CURRENT_TIMESTAMP;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- CREATE TRIGGERS
-- =====================================================

-- Employees table triggers
CREATE TRIGGER tr_employees_updated_at
    BEFORE UPDATE ON employees
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER tr_employees_prevent_deleted_update
    BEFORE UPDATE ON employees
    FOR EACH ROW
    EXECUTE FUNCTION prevent_deleted_record_update();

CREATE TRIGGER tr_employees_audit
    AFTER INSERT OR UPDATE OR DELETE ON employees
    FOR EACH ROW
    EXECUTE FUNCTION audit_log_changes();

CREATE TRIGGER tr_employees_auto_terminate
    BEFORE UPDATE ON employees
    FOR EACH ROW
    EXECUTE FUNCTION auto_terminate_employee();

-- Departments table triggers
CREATE TRIGGER tr_departments_updated_at
    BEFORE UPDATE ON departments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER tr_departments_audit
    AFTER INSERT OR UPDATE OR DELETE ON departments
    FOR EACH ROW
    EXECUTE FUNCTION audit_log_changes();

-- Dept_emp table triggers
CREATE TRIGGER tr_dept_emp_updated_at
    BEFORE UPDATE ON dept_emp
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER tr_dept_emp_prevent_overlap
    BEFORE INSERT OR UPDATE ON dept_emp
    FOR EACH ROW
    EXECUTE FUNCTION prevent_overlapping_dept_assignments();

CREATE TRIGGER tr_dept_emp_audit
    AFTER INSERT OR UPDATE OR DELETE ON dept_emp
    FOR EACH ROW
    EXECUTE FUNCTION audit_log_changes();

-- Salaries table triggers
CREATE TRIGGER tr_salaries_updated_at
    BEFORE UPDATE ON salaries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER tr_salaries_validate_change
    BEFORE INSERT ON salaries
    FOR EACH ROW
    EXECUTE FUNCTION validate_salary_change();

CREATE TRIGGER tr_salaries_audit
    AFTER INSERT OR UPDATE OR DELETE ON salaries
    FOR EACH ROW
    EXECUTE FUNCTION audit_log_changes();

-- =====================================================
-- COMMENTS
-- =====================================================
COMMENT ON FUNCTION update_updated_at_column() IS 'Automatically updates updated_at and increments version';
COMMENT ON FUNCTION audit_log_changes() IS 'Logs all changes to audit_log table';
COMMENT ON FUNCTION calculate_age(DATE) IS 'Calculates age from birth date';
COMMENT ON FUNCTION calculate_years_of_service(DATE, DATE) IS 'Calculates years of service';
COMMENT ON FUNCTION get_current_salary(INTEGER) IS 'Returns current salary for an employee';
COMMENT ON FUNCTION get_current_department(INTEGER) IS 'Returns current department for an employee';
COMMENT ON FUNCTION validate_salary_change() IS 'Validates salary changes against business rules';
COMMENT ON FUNCTION auto_terminate_employee() IS 'Automatically terminates employee and related records';
COMMENT ON FUNCTION cleanup_old_audit_logs() IS 'Removes audit logs older than 1 year';
COMMENT ON FUNCTION cleanup_expired_cache() IS 'Removes expired cache entries';
