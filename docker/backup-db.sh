#!/bin/sh
set -e

# Backup script supporting SQLite and PostgreSQL (including SQLAlchemy style URIs)
# Writes backups into $BACKUP_DIR (default /backups), applies retention, writes a status file,
# and optionally uploads to S3 when AWS_S3_BUCKET is provided.

BACKUP_DIR=${BACKUP_DIR:-/backups}
# POSIX-safe DB URI fallback: prefer SQLALCHEMY_DATABASE_URI, then DATABASE_URL
if [ -n "$SQLALCHEMY_DATABASE_URI" ]; then
  DB_URI="$SQLALCHEMY_DATABASE_URI"
elif [ -n "$DATABASE_URL" ]; then
  DB_URI="$DATABASE_URL"
else
  DB_URI=""
fi
# RETENTION default
if [ -n "$BACKUP_RETENTION_DAYS" ]; then
  # Sanitize: remove quotes and any non-digit characters (like \r from Windows env files)
  RETENTION_DAYS=$(echo "$BACKUP_RETENTION_DAYS" | tr -d '"' | tr -cd '0-9')
else
  RETENTION_DAYS=2
fi

timestamp() {
  date -u +"%Y%m%dT%H%M%SZ"
}

fail() {
  printf '%s - backup-db: ERROR: %s\n' "$(timestamp)" "$1" 1>&2
  exit 1
}

if [ -z "$DB_URI" ]; then
  fail "No database URI found. Set SQLALCHEMY_DATABASE_URI or DATABASE_URL."
fi

# Some orchestrators wrap env values in quotes; strip matching leading/trailing quotes.
if [ "${DB_URI#\"}" != "$DB_URI" ] && [ "${DB_URI%\"}" != "$DB_URI" ]; then
  DB_URI=${DB_URI#\"}
  DB_URI=${DB_URI%\"}
fi

mkdir -p "$BACKUP_DIR" || fail "Could not create backup dir: $BACKUP_DIR"

# Determine scheme (e.g. "sqlite", "postgresql+psycopg") and normalize
SCHEME_WITH_PLUS=${DB_URI%%:*}
SCHEME=${SCHEME_WITH_PLUS%%+*}

if [ "$SCHEME" = "sqlite" ]; then
  # Normalize sqlite path
  DB_PATH=${DB_URI#sqlite:///}
  DB_PATH=${DB_URI#sqlite://}
  if [ -z "$DB_PATH" ]; then
    fail "Could not determine sqlite file path from URI: $DB_URI"
  fi

  OUT_FILE="$BACKUP_DIR/sqlite-$(timestamp).db"
  printf '%s - backup-db: copying sqlite db %s -> %s\n' "$(timestamp)" "$DB_PATH" "$OUT_FILE"
  if [ -f "$DB_PATH" ]; then
    TMP_OUT="$OUT_FILE.tmp"
    cp -a "$DB_PATH" "$TMP_OUT" || fail "Failed to copy sqlite db"
    gzip -9 "$TMP_OUT" || true
    OUT_FILE_GZ="$OUT_FILE.gz"
    mv "$TMP_OUT.gz" "$OUT_FILE_GZ" 2>/dev/null || mv "$TMP_OUT" "$OUT_FILE" || true
    printf '%s - backup-db: success: %s\n' "$(timestamp)" "${OUT_FILE_GZ:-$OUT_FILE}"
    LAST_CREATED="${OUT_FILE_GZ:-$OUT_FILE}"
  else
    fail "Sqlite DB file not found at $DB_PATH"
  fi

elif [ "$SCHEME" = "postgres" ] || [ "$SCHEME" = "postgresql" ]; then
  if ! command -v pg_dump >/dev/null 2>&1; then
    fail "pg_dump not found in image. Install PostgreSQL client utilities to enable pg backups."
  fi

  # Build PG_URI by replacing the scheme section (before ://) with the normalized scheme.
  # This is POSIX-safe (avoids bash-only ${var/...} substitution).
  rest=${DB_URI#*://}
  PG_URI="$SCHEME://$rest"

  STAMP=$(timestamp)
  OUT_FILE_BASE="$BACKUP_DIR/pg_dump-$STAMP.sql"
  OUT_FILE_GZ="$OUT_FILE_BASE.gz"
  printf '%s - backup-db: running pg_dump for %s -> %s\n' "$(timestamp)" "$PG_URI" "$OUT_FILE_GZ"
  if pg_dump "$PG_URI" --format=plain --no-owner --no-privileges --file="$OUT_FILE_BASE"; then
    if gzip -9 "$OUT_FILE_BASE"; then
      # gzip automatically appends .gz and removes the original
      printf '%s - backup-db: success: %s\n' "$(timestamp)" "$OUT_FILE_GZ"
      LAST_CREATED="$OUT_FILE_GZ"
    else
      rm -f "$OUT_FILE_BASE"
      fail "Failed to compress pg_dump output"
    fi
  else
    rm -f "$OUT_FILE_BASE"
    fail "pg_dump failed"
  fi

else
  fail "Unsupported or unknown DB URI scheme: $DB_URI"
fi

# Retention: delete backups older than RETENTION_DAYS
# Debug retention value
printf '%s - backup-db: DEBUG: RETENTION_DAYS=%s\n' "$(timestamp)" "$RETENTION_DAYS"

if [ -n "$RETENTION_DAYS" ] && [ "$RETENTION_DAYS" -gt 0 ]; then
  RETENTION_MINUTES=$((RETENTION_DAYS * 1440))
  printf '%s - backup-db: cleaning backups older than %s days (%s minutes) in %s\n' "$(timestamp)" "$RETENTION_DAYS" "$RETENTION_MINUTES" "$BACKUP_DIR"
  find "$BACKUP_DIR" -mindepth 1 -type f -mmin +"$RETENTION_MINUTES" -print -exec rm -f -- {} + || true
  printf '%s - backup-db: retention pass complete\n' "$(timestamp)"
fi

# Write status file
STATUS_FILE="$BACKUP_DIR/backup-status.json"
export STATUS_GEN_BACKUP_DIR="$BACKUP_DIR"
export STATUS_GEN_FILE="$STATUS_FILE"
export STATUS_GEN_LAST_TS="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
export STATUS_GEN_LAST_FILE="${LAST_CREATED:-null}"

python -c "
import json
import os

backup_dir = os.environ['STATUS_GEN_BACKUP_DIR']
status_file = os.environ['STATUS_GEN_FILE']
last_backup = os.environ['STATUS_GEN_LAST_TS']
last_file = os.environ['STATUS_GEN_LAST_FILE']

files = []
try:
    if os.path.exists(backup_dir):
        # List files, exclude status file, sort by mtime desc
        all_files = [f for f in os.listdir(backup_dir) 
                     if os.path.isfile(os.path.join(backup_dir, f)) 
                     and f != 'backup-status.json']
        files = sorted(all_files, key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)), reverse=True)
except Exception as e:
    print(f'Error listing backups: {e}')

data = {
    'last_backup': last_backup,
    'last_file': last_file,
    'backups': files
}

with open(status_file, 'w') as f:
    json.dump(data, f, indent=2)
" || true

printf '%s - backup-db: wrote status to %s\n' "$(timestamp)" "$STATUS_FILE"

# Optional S3 upload
if [ -n "$AWS_S3_BUCKET" ]; then
  echo "$(timestamp) - backup-db: uploading ${LAST_CREATED:-} to s3://$AWS_S3_BUCKET/$AWS_S3_PREFIX"
  python /app/s3_upload.py "${LAST_CREATED:-}" "$AWS_S3_BUCKET" "${AWS_S3_PREFIX:-}"
fi

exit 0
