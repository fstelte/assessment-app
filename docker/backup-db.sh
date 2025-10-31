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
  RETENTION_DAYS="$BACKUP_RETENTION_DAYS"
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

mkdir -p "$BACKUP_DIR" || fail "Could not create backup dir: $BACKUP_DIR"

# Determine scheme (e.g. "sqlite", "postgresql+psycopg") and normalize
SCHEME_WITH_PLUS=$(printf '%s' "$DB_URI" | sed -n 's,\([a-zA-Z0-9+._-]*\):.*,\1,p')
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

  OUT_FILE_GZ="$BACKUP_DIR/pg_dump-$(timestamp).sql.gz"
  printf '%s - backup-db: running pg_dump for %s -> %s\n' "$(timestamp)" "$PG_URI" "$OUT_FILE_GZ"
  pg_dump "$PG_URI" --format=plain --no-owner --no-privileges 2>/dev/null | gzip > "$OUT_FILE_GZ" || fail "pg_dump failed"
  printf '%s - backup-db: success: %s\n' "$(timestamp)" "$OUT_FILE_GZ"
  LAST_CREATED="$OUT_FILE_GZ"

else
  fail "Unsupported or unknown DB URI scheme: $DB_URI"
fi

# Retention: delete backups older than RETENTION_DAYS
if [ -n "$RETENTION_DAYS" ] && [ "$RETENTION_DAYS" -gt 0 ] 2>/dev/null; then
  printf '%s - backup-db: cleaning backups older than %s days in %s\n' "$(timestamp)" "$RETENTION_DAYS" "$BACKUP_DIR"
  find "$BACKUP_DIR" -mindepth 1 -type f -mtime +$(expr "$RETENTION_DAYS" - 1) -print -exec rm -f -- {} + || true
  printf '%s - backup-db: retention pass complete\n' "$(timestamp)"
fi

# Write status file
STATUS_FILE="$BACKUP_DIR/backup-status.json"
cat > "$STATUS_FILE" <<JSON || true
{
  "last_backup": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
  "last_file": "${LAST_CREATED:-null}"
}
JSON
printf '%s - backup-db: wrote status to %s\n' "$(timestamp)" "$STATUS_FILE"

# Optional S3 upload
if [ -n "$AWS_S3_BUCKET" ]; then
  echo "$(timestamp) - backup-db: uploading ${LAST_CREATED:-} to s3://$AWS_S3_BUCKET/$AWS_S3_PREFIX"
  python /app/s3_upload.py "${LAST_CREATED:-}" "$AWS_S3_BUCKET" "${AWS_S3_PREFIX:-}"
fi

exit 0
