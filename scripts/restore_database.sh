#!/usr/bin/env bash
# ==============================================================================
# CIVICSOL - Automated PostgreSQL Database Restore Script
# Safely restores a verified PostgreSQL backup archive.
# Requires explicit confirmation to prevent accidental overwrites.
# ==============================================================================

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <backup_file.sql> [--confirm]"
    echo "Example: $0 backups/civicsol_backup_20261030_190520.sql --confirm"
    exit 1
fi

BACKUP_FILE="$1"
CONFIRM_FLAG="${2:-}"

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-civicsol}"
DB_USER="${DB_USER:-civicsol_user}"
CONTAINER_NAME="${CONTAINER_NAME:-civicsol_postgres}"

if [[ ! -f "${BACKUP_FILE}" ]]; then
    echo "ERROR: Backup file '${BACKUP_FILE}' does not exist!"
    exit 1
fi

if [[ "${CONFIRM_FLAG}" != "--confirm" ]]; then
    echo "SAFETY WARNING:"
    echo "This operation will restore '${BACKUP_FILE}' into '${DB_NAME}'."
    echo "Existing records may be overwritten."
    echo "To proceed, run: $0 '${BACKUP_FILE}' --confirm"
    exit 1
fi

# Verify checksum if checksum file exists
CHECKSUM_FILE="${BACKUP_FILE}.sha256"
if [[ -f "${CHECKSUM_FILE}" ]]; then
    echo "Verifying SHA-256 checksum..."
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 -c "${CHECKSUM_FILE}"
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum -c "${CHECKSUM_FILE}"
    fi
fi

echo "=================================================="
echo "Restoring database from: ${BACKUP_FILE}"
echo "=================================================="

if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Restoring via Docker container '${CONTAINER_NAME}'..."
    docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" < "${BACKUP_FILE}"
else
    echo "Restoring via host psql binary..."
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" < "${BACKUP_FILE}"
fi

echo "Database restore completed successfully."

