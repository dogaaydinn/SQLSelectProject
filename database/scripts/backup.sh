#!/bin/bash

# =====================================================
# Database Backup Script
# Description: Automated PostgreSQL backup with rotation
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
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
COMPRESSION="${COMPRESSION:-gzip}"
S3_BUCKET="${BACKUP_S3_BUCKET:-}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql"
LOG_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

log_info "Starting backup of database: $DB_NAME"

# Check if PostgreSQL is accessible
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
    log_error "PostgreSQL is not accessible at $DB_HOST:$DB_PORT"
    exit 1
fi

log_info "Database connection verified"

# Perform the backup
log_info "Creating backup file: $BACKUP_FILE"

if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --format=plain \
    --no-owner \
    --no-acl \
    --verbose \
    --file="$BACKUP_FILE" 2>> "$LOG_FILE"; then
    log_info "Database dump completed successfully"
else
    log_error "Database dump failed"
    exit 1
fi

# Get backup file size
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log_info "Backup file size: $BACKUP_SIZE"

# Compress the backup
if [ "$COMPRESSION" = "gzip" ]; then
    log_info "Compressing backup with gzip..."
    if gzip -9 "$BACKUP_FILE"; then
        BACKUP_FILE="${BACKUP_FILE}.gz"
        COMPRESSED_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log_info "Compression completed. Compressed size: $COMPRESSED_SIZE"
    else
        log_error "Compression failed"
        exit 1
    fi
elif [ "$COMPRESSION" = "bzip2" ]; then
    log_info "Compressing backup with bzip2..."
    if bzip2 -9 "$BACKUP_FILE"; then
        BACKUP_FILE="${BACKUP_FILE}.bz2"
        COMPRESSED_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log_info "Compression completed. Compressed size: $COMPRESSED_SIZE"
    else
        log_error "Compression failed"
        exit 1
    fi
fi

# Upload to S3 if configured
if [ -n "$S3_BUCKET" ]; then
    log_info "Uploading backup to S3: s3://$S3_BUCKET/"
    if command -v aws &> /dev/null; then
        if aws s3 cp "$BACKUP_FILE" "s3://$S3_BUCKET/$(basename "$BACKUP_FILE")" \
            --storage-class STANDARD_IA \
            --metadata "db_name=$DB_NAME,timestamp=$TIMESTAMP"; then
            log_info "S3 upload completed successfully"
        else
            log_warn "S3 upload failed, but local backup is available"
        fi
    else
        log_warn "AWS CLI not found, skipping S3 upload"
    fi
fi

# Cleanup old backups (retention policy)
log_info "Cleaning up backups older than $RETENTION_DAYS days"
OLD_BACKUPS=$(find "$BACKUP_DIR" -name "${DB_NAME}_*.sql*" -type f -mtime +$RETENTION_DAYS)

if [ -n "$OLD_BACKUPS" ]; then
    echo "$OLD_BACKUPS" | while read -r old_backup; do
        log_info "Removing old backup: $old_backup"
        rm -f "$old_backup"
    done
else
    log_info "No old backups to remove"
fi

# Create backup manifest
MANIFEST_FILE="${BACKUP_DIR}/backup_manifest.json"
cat > "$MANIFEST_FILE" << EOF
{
  "timestamp": "$TIMESTAMP",
  "database": "$DB_NAME",
  "host": "$DB_HOST",
  "port": $DB_PORT,
  "backup_file": "$(basename "$BACKUP_FILE")",
  "size": "$COMPRESSED_SIZE",
  "compression": "$COMPRESSION",
  "s3_bucket": "$S3_BUCKET",
  "retention_days": $RETENTION_DAYS
}
EOF

log_info "Backup manifest created: $MANIFEST_FILE"

# Verify backup integrity
log_info "Verifying backup integrity..."
if [ "$COMPRESSION" = "gzip" ]; then
    if gzip -t "$BACKUP_FILE" 2>> "$LOG_FILE"; then
        log_info "Backup integrity verified successfully"
    else
        log_error "Backup integrity check failed!"
        exit 1
    fi
fi

# Send notification (webhook or email - configure as needed)
if [ -n "${BACKUP_WEBHOOK_URL:-}" ]; then
    curl -X POST "$BACKUP_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{\"status\": \"success\", \"database\": \"$DB_NAME\", \"timestamp\": \"$TIMESTAMP\", \"size\": \"$COMPRESSED_SIZE\"}" \
        > /dev/null 2>&1 || log_warn "Webhook notification failed"
fi

log_info "Backup completed successfully!"
log_info "Backup file: $BACKUP_FILE"
log_info "Log file: $LOG_FILE"

exit 0
