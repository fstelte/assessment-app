---
type: decision
id: 20261125-0753-pg-password-via-pgpassword-env
date: 2026-11-25
status: accepted
supersedes: null
superseded_by: null
impacts:
  - docker/restore/restore_db.py
  - docker/backup-db.sh
  - scaffold/apps/admin/backup_utils.py
tags: [security, logging, postgres, backup, restore]
participants: [Ferry Stelte, Claude]
---

# Postgres client tools get the password through PGPASSWORD, never in the URI argument

## Context

The restore container, the backup container and the app's manual backup run
`psql`, `pg_restore` and `pg_dump` with the full `postgresql://user:PASSWORD@host/db`
URI as a command-line argument. Because of that, the password ends up in:

- the restore log (`executing: psql postgresql://user:PASSWORD@...`, `run_command`);
- the text of `CalledProcessError`, which is logged as `restore failed: ...` and
  stored as `session_rotation.error` in the restore state file;
- the backup log (`backup-db: running pg_dump for postgresql://user:PASSWORD@...`);
- `ps` / `/proc/<pid>/cmdline` while the command runs.

## Options Considered

- **A: remove the password from the URI and pass it through the `PGPASSWORD`
  environment variable of the child process (chosen).**
- B: keep the URI as it is and mask passwords when logging: rejected. Every
  current and future log line and exception path would need to remember to
  mask, the state file would still need its own masking, and argv would still
  show the password.
- A+B (both): not chosen for now. Once the password is no longer in argv, the
  masking layer would have nothing to mask in these paths. Masking is still used
  where the URL text itself has to be printed (`wait_for_db.py`, decision 0800).
- C: a temporary `.pgpass` file (`PGPASSFILE`): rejected. It needs a 0600 temp
  file and cleanup on every exit path, for no gain on Linux, where another user
  can't read a process's environment.

## Decision

- Before running a Postgres client tool, the URI is split into a URI without a
  password and an environment with `PGPASSWORD` set (the child process only;
  the parent's `os.environ` is not changed).
- Applies to: every `psql`/`pg_restore` call in `restore_db.py` (including
  `psql_scalar`), `pg_dump` in `backup-db.sh`, and `pg_dump` in
  `create_postgres_backup`.
- The password is URL-decoded before it goes into `PGPASSWORD`, so encoded
  characters (`%40` for `@`) work the same as they do in the URI.

## Consequences

### Positive
- ✅ Log lines, exception text, the state file and `ps` don't contain the password,
  because the password is not in the command.
- ✅ No list of places to mask that has to be kept up to date.

### Negative
- ⚠️ `PGPASSWORD` is visible in `/proc/<pid>/environ` of the child process, but
  only to the same user or root, while argv can be read by any user on the host.
  Accepted. Threat model: people and systems that read logs or list processes.
  `DATABASE_URL` in `docker inspect` / env files stays readable by whoever
  controls Docker, who can reach the database anyway.
- ⚠️ In `backup-db.sh` the password is a command prefix for `pg_dump`, not
  exported (decision 0830).
- ⚠️ A `PGPASSWORD` that is already set in the container environment is
  overwritten for the child process when the URI has a password.

## Related Decisions

- [[20261107-0855-restore-invalidates-all-sessions]] (`psql_scalar` for the token rotation)
