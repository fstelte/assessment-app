#!/bin/sh
STATUS_FILE=${BACKUP_STATUS_FILE:-/backups/backup-status.json}
MAX_AGE_SECONDS=${HEALTH_MAX_AGE_SECONDS:-172800} # default 2 days

if [ ! -f "$STATUS_FILE" ]; then
  echo "healthcheck: status file not found: $STATUS_FILE" 1>&2
  exit 1
fi

# Expect JSON with last_backup_ts as ISO8601
LAST_TS=$(sed -n "s/.*\"last_backup\":\s*\"\([0-9TZ:\-]*\)\".*/\1/p" "$STATUS_FILE" | tail -n1)
if [ -z "$LAST_TS" ]; then
  echo "healthcheck: last_backup not found in $STATUS_FILE" 1>&2
  exit 1
fi

# Parse ISO timestamp into seconds since epoch
LAST_EPOCH=$(date -u -d "$LAST_TS" +%s 2>/dev/null || true)
if [ -z "$LAST_EPOCH" ]; then
  echo "healthcheck: could not parse timestamp $LAST_TS" 1>&2
  exit 1
fi

NOW=$(date -u +%s)
AGE=$((NOW - LAST_EPOCH))
if [ "$AGE" -le "$MAX_AGE_SECONDS" ]; then
  echo "healthcheck: ok, last backup $AGE seconds ago"
  exit 0
else
  echo "healthcheck: stale backup, last backup $AGE seconds ago" 1>&2
  exit 2
fi
