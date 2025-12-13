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

# Wait for Postgres if applicable
if command -v pg_isready >/dev/null 2>&1 && ([ -n "$DATABASE_URL" ] || [ -n "$SQLALCHEMY_DATABASE_URI" ]); then
  DB_URI="${DATABASE_URL:-$SQLALCHEMY_DATABASE_URI}"
  # Normalize scheme for pg_isready (remove +psycopg etc)
  SCHEME_WITH_PLUS=${DB_URI%%:*}
  SCHEME=${SCHEME_WITH_PLUS%%+*}

  if [ "$SCHEME" = "postgres" ] || [ "$SCHEME" = "postgresql" ]; then
      # Reconstruct URI with simple scheme
      rest=${DB_URI#*://}
      PG_URI="$SCHEME://$rest"

      printf '%s - backup-entrypoint: waiting for database to be ready...\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

      # Wait loop (max 60s)
      RETRIES=30
      while [ $RETRIES -gt 0 ]; do
        if pg_isready -d "$PG_URI" -t 2 >/dev/null 2>&1; then
           printf '%s - backup-entrypoint: database is ready.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
           break
        fi
        RETRIES=$((RETRIES-1))
        sleep 2
      done
  fi
fi

while true; do
  /app/backup-db.sh || true
  sleep "$INTERVAL"
done
