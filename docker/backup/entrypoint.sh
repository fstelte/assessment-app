#!/bin/sh
set -e

# Runs the /app/backup-db.sh script periodically. Designed to be run in a dedicated container
# with /backups mounted to a host directory.

INTERVAL=${BACKUP_INTERVAL_SECONDS:-86400}

if [ -z "$INTERVAL" ]; then
  INTERVAL=86400
fi

printf '%s - backup-entrypoint: starting backup loop (interval=%s seconds)\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$INTERVAL"

# Start status server in background
if command -v python >/dev/null 2>&1; then
  ( python /app/serve-status.py & ) || true
fi

while true; do
  /app/backup-db.sh || true
  sleep "$INTERVAL"
done
