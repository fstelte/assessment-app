---
type: decision
id: 20261125-0805-pg-credential-helpers-inline-per-script
date: 2026-11-25
status: accepted
supersedes: null
superseded_by: null
impacts:
  - docker/restore/restore_db.py
  - docker/backup-db.sh
  - docker/wait_for_db.py
  - scaffold/apps/admin/backup_utils.py
tags: [security, postgres, docker, boundaries]
participants: [Ferry Stelte, Claude]
---

# Password-stripping and masking helpers are inline in each script

## Context

The fix ([[20261125-0753-pg-password-via-pgpassword-env]]) touches four scripts that
run in three images: restore (copies only `restore_db.py`), backup (`backup-db.sh`,
POSIX sh, image has Python) and app (`scaffold/`, plus `/app/docker/wait_for_db.py`).

## Options Considered

- **A: a small inline helper in each script (chosen).**
- B: one shared `docker/pg_uri.py`: rejected. It needs extra `COPY` lines in the
  restore and backup Dockerfiles, and `scaffold/` would either import from `docker/`
  (crossing a module boundary, constitution I) or keep its own copy anyway.

## Decision

- `restore_db.py` and `backup_utils.py` each get a function of about 10 lines that
  takes a URI and returns `(uri_without_password, env_with_PGPASSWORD)`:
  `urlsplit`, `unquote(password)`, netloc rebuilt as `user@host:port`, query kept.
- `backup-db.sh` gets the stripped URI and the password from two inline
  `python3 -c` calls that read the URI from an **environment variable**, not argv,
  so the URI never appears in a process argument (details in decision 0830).
- `docker/backup/entrypoint.sh` needs no helper: `pg_isready` gets the URI
  without userinfo (`${rest##*@}`).
- `wait_for_db.py` gets only the mask helper
  ([[20261125-0800-wait-for-db-masked-url-on-parse-error]]); it doesn't run client tools.
- Each copy has its own tests.

## Consequences

### Positive
- ✅ No Dockerfile changes, no import across a module boundary.
- ✅ Each script stays self-contained, as it is today.

### Negative
- ⚠️ The split logic exists twice in Python and once in the shell python snippet;
  a fix in one has to be repeated in the others. The tests keep them in line.
