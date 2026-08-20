#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

BACKUP_DIR="${WPG_BACKUP_DIR:-/var/backups/wpg-bos}"
RETENTION_DAYS="${WPG_BACKUP_RETENTION_DAYS:-14}"

required_variables=(
    POSTGRES_DB
    POSTGRES_USER
    POSTGRES_PASSWORD
    POSTGRES_HOST
    POSTGRES_PORT
)

for variable_name in "${required_variables[@]}"; do
    if [[ -z "${!variable_name:-}" ]]; then
        echo "Required variable ${variable_name} is missing." >&2
        exit 1
    fi
done

mkdir -p "${BACKUP_DIR}"

timestamp="$(date -u +%Y%m%d_%H%M%S)"
backup_name="${POSTGRES_DB}_${timestamp}.dump"
partial_path="${BACKUP_DIR}/${backup_name}.partial"
backup_path="${BACKUP_DIR}/${backup_name}"
checksum_path="${backup_path}.sha256"

export PGPASSWORD="${POSTGRES_PASSWORD}"

cleanup_partial() {
    if [[ -f "${partial_path}" ]]; then
        rm -f -- "${partial_path}"
    fi
}

trap cleanup_partial EXIT

pg_dump \
    --host="${POSTGRES_HOST}" \
    --port="${POSTGRES_PORT}" \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    --format=custom \
    --no-owner \
    --no-privileges \
    --file="${partial_path}"

pg_restore --list "${partial_path}" >/dev/null

mv -- "${partial_path}" "${backup_path}"
sha256sum "${backup_path}" > "${checksum_path}"

find "${BACKUP_DIR}" \
    -maxdepth 1 \
    -type f \
    \( -name "*.dump" -o -name "*.dump.sha256" \) \
    -mtime "+${RETENTION_DAYS}" \
    -delete

trap - EXIT

echo "Database backup created: ${backup_path}"
echo "Checksum created: ${checksum_path}"