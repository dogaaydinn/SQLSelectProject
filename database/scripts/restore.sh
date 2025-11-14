#!/bin/bash

# =====================================================
# Database Restore Script
# Description: Restore PostgreSQL database from backup
# Author: Enterprise Architecture Team
# Date: 2025-11-14
# =====================================================

set -euo pipefail

# Configuration
DB_NAME="${POSTGRES_DB:-employees}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_FILE="${1:-}"
LOG_FILE="${BACKUP_DIR}/restore_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Usage information
usage() {
    echo -e "${BLUE}Usage:${NC} $0 <backup_file>"
    echo ""
    echo "Examples:"
    echo "  $0 /backups/employees_20231114_120000.sql.gz"
    echo "  $0 employees_20231114_120000.sql.gz  (searches in BACKUP_DIR)"
    echo ""
    echo "Available backups:"
    find "$BACKUP_DIR" -name "${DB_NAME}_*.sql*" -type f -printf "%T@ %p\n" | sort -rn | head -10 | awk '{print "  " $2}'
    exit 1
}

# Check if backup file is provided
if [ -z "$BACKUP_FILE" ]; then
    log_error "No backup file specified"
    usage
fi

# If backup file doesn't have full path, look in BACKUP_DIR
if [ ! -f "$BACKUP_FILE" ]; then
    BACKUP_FILE="${BACKUP_DIR}/${BACKUP_FILE}"
fi

# Verify backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    log_error "Backup file not found: $BACKUP_FILE"
    usage
fi

log_info "Starting database restore"
log_info "Backup file: $BACKUP_FILE"
log_info "Target database: $DB_NAME"

# Confirmation prompt
echo -e "${YELLOW}WARNING:${NC} This will restore the database ${RED}$DB_NAME${NC} from backup."
echo -e "${YELLOW}WARNING:${NC} All current data will be ${RED}REPLACED${NC}."
echo -e "Backup file: $BACKUP_FILE"
read -p "Are you sure you want to continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log_info "Restore cancelled by user"
    exit 0
fi

# Check if PostgreSQL is accessible
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
    log_error "PostgreSQL is not accessible at $DB_HOST:$DB_PORT"
    exit 1
fi

log_info "Database connection verified"

# Create pre-restore backup
PRE_RESTORE_BACKUP="${BACKUP_DIR}/${DB_NAME}_pre_restore_$(date +%Y%m%d_%H%M%S).sql.gz"
log_info "Creating pre-restore backup: $PRE_RESTORE_BACKUP"

if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --format=plain --no-owner --no-acl | gzip > "$PRE_RESTORE_BACKUP" 2>> "$LOG_FILE"; then
    log_info "Pre-restore backup created successfully"
else
    log_warn "Pre-restore backup failed, continuing anyway..."
fi

# Terminate active connections to the database
log_info "Terminating active connections..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres << EOF >> "$LOG_FILE" 2>&1
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '$DB_NAME'
  AND pid <> pg_backend_pid();
EOF

# Drop and recreate database
log_info "Dropping database: $DB_NAME"
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres \
    -c "DROP DATABASE IF EXISTS $DB_NAME;" >> "$LOG_FILE" 2>&1; then
    log_info "Database dropped successfully"
else
    log_error "Failed to drop database"
    exit 1
fi

log_info "Creating database: $DB_NAME"
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres \
    -c "CREATE DATABASE $DB_NAME WITH ENCODING='UTF8' LC_COLLATE='en_US.UTF-8' LC_CTYPE='en_US.UTF-8';" >> "$LOG_FILE" 2>&1; then
    log_info "Database created successfully"
else
    log_error "Failed to create database"
    exit 1
fi

# Decompress and restore
log_info "Restoring database from backup..."

if [[ "$BACKUP_FILE" == *.gz ]]; then
    log_info "Decompressing gzip backup..."
    if gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >> "$LOG_FILE" 2>&1; then
        log_info "Restore completed successfully"
    else
        log_error "Restore failed"
        log_error "Check log file: $LOG_FILE"
        exit 1
    fi
elif [[ "$BACKUP_FILE" == *.bz2 ]]; then
    log_info "Decompressing bzip2 backup..."
    if bunzip2 -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >> "$LOG_FILE" 2>&1; then
        log_info "Restore completed successfully"
    else
        log_error "Restore failed"
        log_error "Check log file: $LOG_FILE"
        exit 1
    fi
else
    log_info "Restoring uncompressed backup..."
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE" >> "$LOG_FILE" 2>&1; then
        log_info "Restore completed successfully"
    else
        log_error "Restore failed"
        log_error "Check log file: $LOG_FILE"
        exit 1
    fi
fi

# Verify restore
log_info "Verifying restore..."
EMPLOYEE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -t -c "SELECT COUNT(*) FROM employees WHERE is_deleted = FALSE;" 2>> "$LOG_FILE" | tr -d ' ')

if [ -n "$EMPLOYEE_COUNT" ] && [ "$EMPLOYEE_COUNT" -gt 0 ]; then
    log_info "Verification successful. Employee count: $EMPLOYEE_COUNT"
else
    log_error "Verification failed. Employee count: ${EMPLOYEE_COUNT:-0}"
    exit 1
fi

# Update statistics
log_info "Updating database statistics..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -c "ANALYZE;" >> "$LOG_FILE" 2>&1

# Refresh materialized views
log_info "Refreshing materialized views..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << EOF >> "$LOG_FILE" 2>&1
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_employee_summary;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_department_summary;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_salary_trends;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_high_performers;
EOF

log_info "Database restore completed successfully!"
log_info "Pre-restore backup saved at: $PRE_RESTORE_BACKUP"
log_info "Log file: $LOG_FILE"

exit 0
