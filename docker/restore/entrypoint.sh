#!/bin/sh
set -e

RESTORE_POLL_INTERVAL=${RESTORE_POLL_INTERVAL:-30}

printf '%s - restore-entrypoint: watching for backups (interval=%ss)\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$RESTORE_POLL_INTERVAL"
exec python /app/restore_db.py
