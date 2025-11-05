#!/bin/sh
set -e

load_env_file() {
  file="$1"
  if [ ! -f "$file" ]; then
    return 1
  fi

  exports=$(python - <<'PY' "$file"
import os
import sys
from pathlib import Path
from string import Template


def parse_env(path: Path) -> None:
  context = dict(os.environ)
  entries: list[tuple[str, str]] = []

  for raw in path.read_text(encoding="utf-8").splitlines():
    stripped = raw.strip()
    if not stripped or stripped.startswith("#"):
      continue

    if "=" not in raw:
      continue

    key, value = raw.split("=", 1)
    key = key.strip()
    if not key:
      continue

    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
      value = value[1:-1]

    entries.append((key, value))

  resolved: dict[str, str] = {}
  for _ in range(len(entries)):
    progress = False
    for key, raw_value in entries:
      if key in resolved:
        continue
      composed_context = dict(context)
      composed_context.update(resolved)
      candidate = Template(raw_value).safe_substitute(composed_context)
      if "${" not in candidate:
        resolved[key] = candidate
        progress = True
    if not progress:
      break

  for key, raw_value in entries:
    value = resolved.get(key)
    if value is None:
      composed_context = dict(context)
      composed_context.update(resolved)
      value = Template(raw_value).safe_substitute(composed_context)
    context[key] = value
    os.environ[key] = value
    print(f"{key}={value}")


parse_env(Path(sys.argv[1]))
PY
)

  if [ -z "$exports" ]; then
    return 0
  fi

  OLDIFS=$IFS
  IFS=
  while IFS='=' read -r key value || [ -n "$key" ]; do
    [ -z "$key" ] && continue
    key_trim=$(printf '%s' "$key" | tr -d ' \t')
    [ -z "$key_trim" ] && continue
    if ! env | grep -q "^${key_trim}="; then
      export "$key_trim=$value"
    fi
  done <<EOF
$exports
EOF
  IFS=$OLDIFS

  return 0
}

for env_file in /app/.env.production /app/.env; do
  if load_env_file "$env_file"; then
    break
  fi
done

python /app/docker/render_maintenance.py

python /app/docker/wait_for_db.py

flask db upgrade

# Background cleaner: remove files and folders inside /app/exports older than 1 day,
# run every 4 hours and emit timestamped logs to stdout/stderr so Docker captures them.
start_exports_cleaner() {
  export_dir="/app/exports"

  # Only start if directory exists to avoid creating it unintentionally.
  if [ -d "$export_dir" ]; then
    (
      while true; do
        if [ -d "$export_dir" ]; then
          # Timestamp start (stdout)
          printf '%s - exports-cleaner: starting sweep\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

          # Find and remove items older than 1 day (mtime +0 means strictly >24h)
          # Use -mindepth 1 to avoid deleting the exports directory itself.
          # Print the removed paths to stdout; errors will go to stderr.
          find "$export_dir" -mindepth 1 -mtime +0 -print -exec rm -rf -- {} + || true

          # Timestamp finish (stdout)
          printf '%s - exports-cleaner: finished sweep\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
        fi

        # Sleep for 4 hours (14400 seconds)
        sleep 14400
      done
    ) &
  fi
}

start_exports_cleaner

exec gunicorn --bind "0.0.0.0:${PORT:-8000}" "scaffold:create_app()"
