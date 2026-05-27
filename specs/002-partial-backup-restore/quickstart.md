# Quickstart: Partial Backup Restore

## Goal

Validate the partial backup restore workflow end to end for both supported database backends without regressing the existing full restore path.

## Prerequisites

1. Configure the existing restore settings:
   - `BACKUP_DIR`
   - `BACKUP_ENCRYPTION_KEY` when testing encrypted backups
   - `RESTORE_WATCH_DIR` for the existing full-restore fallback path
2. Have at least one SQLite backup and one PostgreSQL plain dump backup available.
3. Use an admin account that can pass the existing fresh-login requirement.

## Implementation Validation Flow

1. Run the targeted admin test slice:

```powershell
poetry run pytest tests/test_admin_routes.py -k partial_restore
```

2. Run any helper/service tests added for backup inspection and restore execution:

```powershell
poetry run pytest tests -k "partial_restore or backup_restore"
```

3. Run a focused manual SQLite check:

```text
- Log in as admin
- Open the backup dashboard
- Start the partial restore workflow
- Upload a SQLite backup
- Inspect the table list
- Verify `users` and related identity tables are visible but not preselected
- Select a small non-identity table set and preview the restore
- Confirm conflicting rows are reported as skipped by default
- Execute and verify only the selected tables changed
```

4. Run a focused manual PostgreSQL check:

```text
- Repeat the same workflow with a `.sql.gz` PostgreSQL backup
- Verify table discovery succeeds from the parsed dump
- Verify unsupported or unparseable dumps are routed to the full-restore fallback messaging
```

5. Confirm audit visibility:

```text
- Open the admin audit trail
- Verify inspect, preview, execute, and completion/failure events contain selected table metadata
```

## Documentation Updates Required Before Ship

1. Update deployment and restore runbook guidance for partial restore behavior.
2. Document the identity/auth restore group and the skip-existing default.
3. Document that unsupported backups remain full-restore-only.
