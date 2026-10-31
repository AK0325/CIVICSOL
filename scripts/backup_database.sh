#!/usr/bin/env bash
# ==============================================================================
# CIVICSOL - Automated PostgreSQL Database Backup Script
# Creates a timestamped, verified PostgreSQL backup with SHA-256 checksums
# and automatic rotation of old archives (retains last 14 backups).
# ==============================================================================

set -euo pipefail

BACKUP_DIR="backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/civicsol_backup_${TIMESTAMP}.sql"
CHECKSUM_FILE="${BACKUP_FILE}.sha256"

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-civicsol}"
DB_USER="${DB_USER:-civicsol_user}"
CONTAINER_NAME="${CONTAINER_NAME:-civicsol_postgres}"

mkdir -p "${BACKUP_DIR}"

echo "=================================================="
echo "CIVICSOL Database Backup Utility"
echo "Target DB: ${DB_NAME} on ${DB_HOST}:${DB_PORT}"
echo "Timestamp: ${TIMESTAMP}"
echo "=================================================="

# Check if Docker container is running; otherwise fallback to local pg_dump
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Dumping via Docker container '${CONTAINER_NAME}'..."
    docker exec -t "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists > "${BACKUP_FILE}"
else
    echo "Dumping via host pg_dump binary..."
    pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists > "${BACKUP_FILE}"
fi

# Validation: ensure backup exists and is non-empty
if [[ ! -s "${BACKUP_FILE}" ]]; then
    echo "ERROR: Backup file ${BACKUP_FILE} was not created or is empty!"
    rm -f "${BACKUP_FILE}"
    exit 1
fi

FILE_SIZE=$(wc -c < "${BACKUP_FILE}" | tr -d ' ')
if [[ "${FILE_SIZE}" -lt 1000 ]]; then
    echo "WARNING: Backup file size (${FILE_SIZE} bytes) is suspiciously small. Please inspect manually."
fi

# Generate SHA-256 Checksum
if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "${BACKUP_FILE}" > "${CHECKSUM_FILE}"
elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${BACKUP_FILE}" > "${CHECKSUM_FILE}"
fi

echo "Backup created successfully:"
echo "  File:     ${BACKUP_FILE} (${FILE_SIZE} bytes)"
if [[ -f "${CHECKSUM_FILE}" ]]; then
    echo "  Checksum: $(cat "${CHECKSUM_FILE}")"
fi

# Backup rotation: Keep only the 14 most recent backups
echo "Applying retention policy (retaining 14 most recent archives)..."
find "${BACKUP_DIR}" -name "civicsol_backup_*.sql" -type f | sort -r | tail -n +15 | while read -r old_file; do
    echo "  Pruning obsolete backup: ${old_file}"
    rm -f "${old_file}" "${old_file}.sha256"
done

echo "Database backup completed successfully."

