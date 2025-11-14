-- =====================================================
-- Migration V4: Advanced Indexing and Query Optimization
-- Description: Create specialized indexes for performance
-- Author: Enterprise Architecture Team
-- Date: 2025-11-14
-- =====================================================

-- =====================================================
-- COMPOSITE INDEXES FOR COMMON QUERIES
-- =====================================================

-- Employee search composite indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_emp_name_status_hire
    ON employees(last_name, first_name, status, hire_date)
    WHERE is_deleted = FALSE;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_emp_dept_salary
    ON employees(emp_no)
    INCLUDE (first_name, last_name, email, status);

-- Department assignment query optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dept_emp_emp_dates
    ON dept_emp(emp_no, from_date, to_date)
    WHERE is_deleted = FALSE AND to_date = '9999-12-31';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dept_emp_dept_dates
    ON dept_emp(dept_no, from_date, to_date)
    WHERE is_deleted = FALSE;

-- Salary range queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_salary_range_current
    ON salaries(salary)
    INCLUDE (emp_no, from_date, currency)
    WHERE is_deleted = FALSE AND to_date = '9999-12-31';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_salary_emp_dates_amount
    ON salaries(emp_no, from_date DESC, salary DESC)
    WHERE is_deleted = FALSE;

-- =====================================================
-- PARTIAL INDEXES FOR SPECIFIC QUERIES
-- =====================================================

-- Active employees only
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_emp_active_only
    ON employees(emp_no, hire_date, email)
    WHERE is_deleted = FALSE AND status = 'Active';

-- High salary earners (for analytics)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_salary_high_earners
    ON salaries(emp_no, salary, from_date)
    WHERE salary > 100000 AND is_deleted = FALSE;

-- Recent hires (last 5 years)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_emp_recent_hires
    ON employees(hire_date DESC, emp_no)
    WHERE hire_date >= CURRENT_DATE - INTERVAL '5 years' AND is_deleted = FALSE;

-- Terminated employees
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_emp_terminated
    ON employees(termination_date, emp_no)
    WHERE status = 'Terminated' AND is_deleted = FALSE;

-- =====================================================
-- EXPRESSION INDEXES
-- =====================================================

-- Full name search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_emp_full_name_lower
    ON employees(LOWER(first_name || ' ' || last_name))
    WHERE is_deleted = FALSE;

-- Email domain search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_emp_email_domain
    ON employees(LOWER(SPLIT_PART(email, '@', 2)))
    WHERE email IS NOT NULL AND is_deleted = FALSE;

-- Year of hire
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_emp_hire_year
    ON employees(EXTRACT(YEAR FROM hire_date))
    WHERE is_deleted = FALSE;

-- Salary year
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_salary_year
    ON salaries(EXTRACT(YEAR FROM from_date), emp_no)
    WHERE is_deleted = FALSE;

-- =====================================================
-- COVERING INDEXES (INCLUDE columns)
-- =====================================================

-- Employee list with common columns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_emp_list_covering
    ON employees(emp_no)
    INCLUDE (first_name, last_name, email, hire_date, status)
    WHERE is_deleted = FALSE;

-- Department list with stats
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dept_list_covering
    ON departments(dept_no)
    INCLUDE (dept_name, location, budget, is_active)
    WHERE is_deleted = FALSE;

-- Current salary lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_salary_current_covering
    ON salaries(emp_no)
    INCLUDE (salary, currency, from_date)
    WHERE to_date = '9999-12-31' AND is_deleted = FALSE;

-- =====================================================
-- BTREE_GIN INDEXES (For mixed queries)
-- =====================================================

-- Employee metadata search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_emp_metadata_gin
    ON employees USING GIN(metadata jsonb_path_ops)
    WHERE metadata IS NOT NULL;

-- Department metadata search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dept_metadata_gin
    ON departments USING GIN(metadata jsonb_path_ops)
    WHERE metadata IS NOT NULL;

-- =====================================================
-- HASH INDEXES (For equality searches)
-- =====================================================

-- UUID lookups (when exact match is needed)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_emp_uuid_hash
    ON employees USING HASH(uuid);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dept_uuid_hash
    ON departments USING HASH(uuid);

-- =====================================================
-- BLOOM INDEXES (For multi-column equality)
-- Requires: CREATE EXTENSION IF NOT EXISTS bloom;
-- =====================================================

-- Uncomment if bloom extension is available
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_emp_bloom_multi
--     ON employees USING bloom(gender, status, country)
--     WHERE is_deleted = FALSE;

-- =====================================================
-- STATISTICS FOR QUERY PLANNER
-- =====================================================

-- Increase statistics target for frequently queried columns
ALTER TABLE employees ALTER COLUMN last_name SET STATISTICS 1000;
ALTER TABLE employees ALTER COLUMN first_name SET STATISTICS 1000;
ALTER TABLE employees ALTER COLUMN hire_date SET STATISTICS 1000;
ALTER TABLE employees ALTER COLUMN status SET STATISTICS 500;

ALTER TABLE salaries ALTER COLUMN salary SET STATISTICS 1000;
ALTER TABLE salaries ALTER COLUMN from_date SET STATISTICS 1000;

ALTER TABLE dept_emp ALTER COLUMN dept_no SET STATISTICS 500;
ALTER TABLE dept_emp ALTER COLUMN from_date SET STATISTICS 500;

-- Create extended statistics for correlated columns
CREATE STATISTICS IF NOT EXISTS stat_emp_name_correlation
    ON first_name, last_name FROM employees;

CREATE STATISTICS IF NOT EXISTS stat_salary_emp_date
    ON emp_no, from_date, salary FROM salaries;

CREATE STATISTICS IF NOT EXISTS stat_dept_emp_dates
    ON emp_no, dept_no, from_date FROM dept_emp;

-- =====================================================
-- QUERY OPTIMIZATION SETTINGS
-- =====================================================

-- Set work_mem for this database (adjust based on available RAM)
-- ALTER DATABASE employees SET work_mem = '256MB';

-- Set random_page_cost (lower for SSD)
-- ALTER DATABASE employees SET random_page_cost = 1.1;

-- Set effective_cache_size (adjust based on available RAM)
-- ALTER DATABASE employees SET effective_cache_size = '4GB';

-- Enable parallel query execution
-- ALTER DATABASE employees SET max_parallel_workers_per_gather = 4;

-- =====================================================
-- INDEX MAINTENANCE FUNCTIONS
-- =====================================================

-- Function to reindex all tables (run during maintenance window)
CREATE OR REPLACE FUNCTION reindex_all_tables()
RETURNS VOID AS $$
DECLARE
    table_record RECORD;
BEGIN
    FOR table_record IN
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE format('REINDEX TABLE CONCURRENTLY %I', table_record.tablename);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to analyze all tables
CREATE OR REPLACE FUNCTION analyze_all_tables()
RETURNS VOID AS $$
DECLARE
    table_record RECORD;
BEGIN
    FOR table_record IN
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE format('ANALYZE %I', table_record.tablename);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to get index usage statistics
CREATE OR REPLACE FUNCTION get_index_usage_stats()
RETURNS TABLE (
    schemaname NAME,
    tablename NAME,
    indexname NAME,
    idx_scan BIGINT,
    idx_tup_read BIGINT,
    idx_tup_fetch BIGINT,
    index_size TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.schemaname,
        s.tablename,
        s.indexname,
        s.idx_scan,
        s.idx_tup_read,
        s.idx_tup_fetch,
        pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size
    FROM pg_stat_user_indexes s
    JOIN pg_index i ON s.indexrelid = i.indexrelid
    WHERE s.schemaname = 'public'
    ORDER BY s.idx_scan ASC;
END;
$$ LANGUAGE plpgsql;

-- Function to identify unused indexes
CREATE OR REPLACE FUNCTION get_unused_indexes()
RETURNS TABLE (
    schemaname NAME,
    tablename NAME,
    indexname NAME,
    index_size TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.schemaname,
        s.tablename,
        s.indexname,
        pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size
    FROM pg_stat_user_indexes s
    JOIN pg_index i ON s.indexrelid = i.indexrelid
    WHERE s.idx_scan = 0
        AND s.schemaname = 'public'
        AND i.indisunique = FALSE
    ORDER BY pg_relation_size(s.indexrelid) DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get table bloat information
CREATE OR REPLACE FUNCTION get_table_bloat()
RETURNS TABLE (
    schemaname NAME,
    tablename NAME,
    actual_size TEXT,
    bloat_percentage NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        schemaname::NAME,
        tablename::NAME,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS actual_size,
        ROUND(
            100 * (pg_total_relation_size(schemaname||'.'||tablename)::NUMERIC /
            NULLIF(pg_total_relation_size(schemaname||'.'||tablename)::NUMERIC, 0)),
            2
        ) AS bloat_percentage
    FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- VACUUM AND MAINTENANCE SETTINGS
-- =====================================================

-- Configure autovacuum for high-traffic tables
ALTER TABLE employees SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02,
    autovacuum_vacuum_cost_delay = 10
);

ALTER TABLE salaries SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02
);

ALTER TABLE dept_emp SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02
);

ALTER TABLE audit_log SET (
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05
);

-- =====================================================
-- COMMENTS
-- =====================================================
COMMENT ON FUNCTION reindex_all_tables() IS 'Reindex all tables concurrently - run during maintenance window';
COMMENT ON FUNCTION analyze_all_tables() IS 'Update statistics for all tables';
COMMENT ON FUNCTION get_index_usage_stats() IS 'Get index usage statistics for optimization';
COMMENT ON FUNCTION get_unused_indexes() IS 'Identify potentially unused indexes';
COMMENT ON FUNCTION get_table_bloat() IS 'Analyze table bloat and recommend vacuum';
