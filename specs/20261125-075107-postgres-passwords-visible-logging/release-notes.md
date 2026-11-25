# Release notes: Postgres password no longer visible in logs (security fix)

## What's new

- **The database password is no longer written to logs.** Before, it appeared in:
  - the restore container log (`executing: psql postgresql://user:PASSWORD@…`) and its
    `restore failed: …` errors;
  - the session-rotation error saved in `restore-state.json`;
  - the backup container log (`running pg_dump for postgresql://user:PASSWORD@…`) and its
    "unsupported scheme" error;
  - the app container log when `DATABASE_URL` could not be read.
- **The password is no longer a process argument.** `psql`, `pg_restore` and `pg_dump` (restore
  container, backup container, manual backup in the admin UI) get it through `PGPASSWORD`, for
  that one process only. `pg_isready` in the backup container gets no credentials at all. `ps` no
  longer shows the password.
- **Clearer startup error.** If `DATABASE_URL` can't be used, `wait_for_db` prints it with the
  password replaced by `***`, plus a hint to URL-encode special characters.

## Who can do what

Nothing changes. No roles, routes or permissions are affected.

## Behaviour changes to be aware of

- **A literal `@` in the `DATABASE_URL` password now stops the app container at startup**
  (`invalid DATABASE_URL '…:***@…': the password contains '@'; …`). Before, SQLAlchemy read
  everything after the first `@` as the host name, so the app failed to connect and printed
  part of the password in every connection error. Encode it as `%40`, or use a password with
  only URL-safe characters (`A–Z a–z 0–9 - . _ ~`). With the example compose files, which put
  the raw `POSTGRES_PASSWORD` into `DATABASE_URL`, the second option is the only one that works.
- The backup script now needs `python` in the backup image to read the URI. The image already
  has it.

## Upgrade

- No database migration, settings or new environment variables.
- **Rotate the Postgres password after upgrading.** Earlier releases wrote it to the backup and
  restore logs. Use `\password` in an interactive `psql`, update `POSTGRES_PASSWORD` /
  `DATABASE_URL` for `web`, `worker`, `db-backup` and `db-restore`, and recreate those
  containers. Changing `POSTGRES_PASSWORD` alone does not change an existing role's password.
  See [Database password](../../docs/deployment.md#database-password).
- Clean up old copies where you can: `docker logs` json files, log shippers or SIEMs, and
  `restore-state.json`.

## Known limitations and follow-ups

- `PGPASSWORD` can be read from `/proc/<pid>/environ` of the client process, but only by the same
  user or root. `DATABASE_URL` stays visible in `docker inspect` and env files, to whoever
  controls Docker on the host.
- A password that ends in a newline is not supported by the backup script.
- `backup-db.sh` still passes the backup encryption key to `encrypt_backup.py` as a command
  argument, so it shows in `ps`. Follow-up.
