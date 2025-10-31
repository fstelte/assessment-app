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

python /app/docker/wait_for_db.py

flask db upgrade

exec gunicorn --bind "0.0.0.0:${PORT:-8000}" "scaffold:create_app()"
