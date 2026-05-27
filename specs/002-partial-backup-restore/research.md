# Research: Partial Backup Restore

## Decision: Execute partial restore in the Flask admin app with backend-specific adapters

**Rationale**: The existing restore watcher only performs whole-database restore operations: SQLite replaces the target database file and PostgreSQL replays a full dump. That path cannot safely execute table-level partial restore for SQLite and would add unnecessary indirection for preview/conflict handling. Running partial restore through admin-owned helper functions keeps authorization, auditing, preview generation, and backend branching in one place.

**Alternatives considered**:
- Reuse the existing restore watcher unchanged by writing generated payloads to `RESTORE_WATCH_DIR`: rejected because SQLite restore currently only copies a full database file.
- Extend the watcher to support partial-restore instructions: rejected for v1 because it would split preview/orchestration logic across Flask and container code without existing support for that protocol.

## Decision: Inspect SQLite backups directly and inspect PostgreSQL backups by parsing the plain pg_dump SQL

**Rationale**: SQLite backups are compressed database files that can be decompressed and queried for table names via `sqlite_master`. PostgreSQL backups in this repo are plain `.sql.gz` dumps created with `pg_dump --format=plain --no-owner --no-privileges`, so table discovery must come from SQL parsing rather than runtime catalog queries. This matches the actual backup formats already produced by the application.

**Alternatives considered**:
- Restore PostgreSQL dumps into a temporary database just to inspect them: rejected because it adds heavy operational dependencies and complicates request-time inspection.
- Restrict partial restore to SQLite only: rejected because the feature must work with the repo's supported deployment backends.

## Decision: Skip conflicting existing rows by default and import only non-conflicting rows

**Rationale**: The clarified product requirement favors safe recovery over destructive overwrite. Default skip-existing behavior makes repeated partial restores deterministic, preserves unrelated current work, and avoids silent replacement of live data while still allowing useful recovery.

**Alternatives considered**:
- Replace existing rows with backup rows: rejected because it is riskier for admin mistakes and harder to reverse.
- Fail the entire table when any conflict exists: rejected because it reduces recovery value and conflicts with the agreed default behavior.

## Decision: Enforce a required identity/auth restore group around `users`

**Rationale**: The actual schema shows `users` depends on `roles`, `user_roles`, `aad_group_mappings`, `mfa_settings`, and `passkey_credentials` for a valid identity state. Allowing `users` to restore alone would create broken authorizations, orphaned MFA or passkey records, or inconsistent Entra mapping behavior.

**Alternatives considered**:
- Allow `users` as a standalone selection: rejected because it violates referential and behavioral integrity.
- Block user-table partial restore entirely: rejected because the clarified spec explicitly allows `user` table selection with strong warnings.

## Decision: Keep preview and restore-run state ephemeral rather than adding new persistent app models

**Rationale**: The repo already has persistent audit logging and no requirement to query restore previews historically outside the audit trail. Using temporary filesystem-backed inspection/preview artifacts keyed to the current admin flow avoids an Alembic migration, keeps the v1 scope smaller, and still supports multi-step preview/execute workflows.

**Alternatives considered**:
- Add database tables for restore previews and restore runs: rejected for v1 because it adds migration and cleanup overhead without clear product value.
- Store all preview data in the browser session: rejected because table/conflict metadata can grow large and is more robust in server-managed temp artifacts.

## Decision: Reuse the existing audit infrastructure for partial restore lifecycle events

**Rationale**: `scaffold/core/audit.py` and `AuditLog` already provide actor, timestamp, request metadata, and structured payload support. Partial restore needs auditable inspect/preview/execute/result events, but not a new audit subsystem.

**Alternatives considered**:
- Add a dedicated restore history model plus a second audit surface: rejected because it duplicates capabilities that already exist.
- Log only final completion events: rejected because failed or partial runs also need accountability.

## Decision: Preserve full restore as the fallback path for unsupported or uninspectable backups

**Rationale**: The spec allows unsupported backup content to remain full-restore-only. Older or malformed PostgreSQL dump files, parse failures, or future backup variants should not block the existing restore capability.

**Alternatives considered**:
- Reject unsupported backups entirely: rejected because it would regress current full-restore behavior.
- Attempt best-effort partial restore for uninspectable backups: rejected because it would be unpredictable and hard to audit.
