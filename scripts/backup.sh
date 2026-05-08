#!/bin/bash
# CryptoScan Machine - PostgreSQL Backup Script
# Run daily via cron: 0 3 * * * /opt/cryptoscan/scripts/backup.sh
set -euo pipefail

BACKUP_DIR="/backups"
DB_NAME="cryptoscan"
DB_USER="cryptoscan"
RETENTION_DAYS=7
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${DATE}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting backup of ${DB_NAME}..."

# Dump database (compressed)
pg_dump -U "${DB_USER}" -d "${DB_NAME}" --no-owner --no-privileges | gzip > "${BACKUP_FILE}"

# Check backup file was created and has content
if [ ! -s "${BACKUP_FILE}" ]; then
    echo "[$(date)] ERROR: Backup file is empty or was not created!"
    exit 1
fi

BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "[$(date)] Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Upload to MinIO (if mc is available)
if command -v mc &> /dev/null; then
    mc cp "${BACKUP_FILE}" local/cryptoscan-backups/ 2>/dev/null && \
        echo "[$(date)] Backup uploaded to MinIO: cryptoscan-backups/${DB_NAME}_${DATE}.sql.gz" || \
        echo "[$(date)] WARNING: MinIO upload failed, backup is local only"
fi

# Remove old backups (keep last N days)
echo "[$(date)] Cleaning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "${DB_NAME}_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

# List remaining backups
REMAINING=$(find "${BACKUP_DIR}" -name "${DB_NAME}_*.sql.gz" | wc -l)
echo "[$(date)] Backup complete. ${REMAINING} backup(s) on disk."
