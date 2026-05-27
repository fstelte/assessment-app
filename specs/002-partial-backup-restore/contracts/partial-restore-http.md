# Contract: Admin Partial Restore HTTP Workflow

## Overview

The application is server-rendered, so the contract is defined as admin routes, submitted form fields, and expected server outcomes rather than a public JSON API.

## Operational References

- The workflow continues to use `BACKUP_DIR`, `BACKUP_ENCRYPTION_KEY`, and `RESTORE_WATCH_DIR` as the authoritative environment-controlled backup and restore settings.
- Operator-facing behavior and fallback guidance must stay aligned with `docs/deployment.md` and `docs/backup_encryption_plan.md`.

## Partial-Restore Eligibility Contract

- Partial restore is eligible only for SQLite `.db.gz`, SQLite `.db.gz.enc`, PostgreSQL plain dump `.sql.gz`, and PostgreSQL plain dump `.sql.gz.enc`.
- PostgreSQL partial restore requires the uploaded dump to be parseable as a plain `pg_dump --format=plain --no-owner --no-privileges` SQL export.
- `.dump`, `.dump.gz`, malformed SQL dumps, unreadable SQLite backups, unusable encrypted backups, and any other uninspectable backup remain full-restore-only in v1.
- A table may appear selectable only when the inspected backup is partial-restore eligible and the table itself is within the supported table-level restore scope.

## Proposed Routes

### `GET /admin/backup/partial-restore`

Renders the partial-restore entry page.

**Response responsibilities**
- Show backup upload/select controls.
- Explain the exact backup variants that are partial-restore eligible and that unsupported backups remain full-restore-only.
- Explain that sensitive identity tables are visible but not preselected.
- Explain that only one partial restore may execute at a time for the environment.

### `POST /admin/backup/partial-restore/inspect`

Accepts a backup file upload and optional encryption key, decrypts/decompresses as needed, inspects the backup, and renders the table-selection step.

**Form fields**
- `backup_file`: required file input
- `encryption_key`: optional password input

**Success contract**
- Creates an `inspection_id`
- Returns table list, backend, source format, inspection expiry metadata, warnings, and full-restore-only status if applicable
- Marks sensitive identity tables as visible but deselected
- Returns row counts as exact values when the backend supports exact inspection and as estimates otherwise

**Failure contract**
- Re-renders form with validation or decryption/inspection error
- Unsupported but recognizable backup variants return full-restore-only guidance without creating a previewable inspection state
- Invalid or unusable decryption keys, malformed PostgreSQL SQL, unreadable SQLite files, and schema-uninspectable backups do not reveal a selectable table list

### `POST /admin/backup/partial-restore/preview`

Builds a preview for the selected tables and calculates dependency/conflict outcomes.

**Form fields**
- `inspection_id`: required hidden input
- `selected_tables[]`: required repeated field with at least one selected table
- `confirm_sensitive_selection`: optional acknowledgement when sensitive tables are selected

**Success contract**
- Normalizes duplicate `selected_tables[]` values before validation or preview assembly
- Expands any required restore groups
- Rejects invalid partial identity-group selections
- Shows per-table conflict counts, dependency warnings, and blocked tables
- Shows whether row counts are exact or estimated for each selected table
- Produces a `run_id` for execution together with preview expiry metadata

**Failure contract**
- Re-renders selection step with validation messages
- Rejects expired or unknown `inspection_id` values and requires a fresh inspection before preview can proceed
- Rejects selections that became unsupported after inspection normalization or required-group expansion

### `POST /admin/backup/partial-restore/execute`

Executes the partial restore with the previously previewed selection.

**Form fields**
- `run_id`: required hidden input
- `confirm_execute`: required confirmation control

**Success contract**
- Requires an unexpired preview generated from the current inspection state
- Revalidates the preview against the current environment immediately before execution and records `revalidated_at`
- Rejects execution when another partial restore is already active for the environment
- Performs backend-specific partial import in dependency-safe order
- Skips conflicting existing rows by default
- Records audit events for execution start and completion
- Redirects to the results page or re-renders with results summary, including blocked tables when some selected items could not run

**Failure contract**
- Records a failed audit event
- Shows table-level failures without losing the overall run context
- Expired previews, stale preview revalidation failures, and concurrent-run conflicts must stop before data changes begin
- Terminal execution failures must preserve enough context to show restored, skipped, blocked, and failed tables in one results view

### `GET /admin/backup/partial-restore/results/<run_id>`

Displays the outcome summary for the executed partial restore.

**Response responsibilities**
- Show restored, skipped, blocked, and failed tables
- Show row counts for imported and skipped conflicts and indicate when preview-time counts were estimates
- Show blocked reasons, warnings acknowledged during preview, and any required restore groups applied automatically
- Show source backup and actor/timing metadata suitable for audit review

## Selection Rules

- At least one table must be selected before preview or execution.
- Any backed-up table may be shown in the selection UI, but only tables from a partial-restore-eligible inspection may proceed to preview or execution.
- `users` may be shown as selectable, but it must not be restored alone.
- Selecting `users` must require the associated identity/auth restore group:
  - `roles`
  - `user_roles`
  - `aad_group_mappings`
  - `mfa_settings`
  - `passkey_credentials`
- Related but non-auto-included tables such as `scim_tokens` and audit-log tables are not part of the required `users` restore group.
- Sensitive identity tables must be visible but deselected by default.
- Sensitive-table warnings must appear when such tables are first shown in preview and again before execution, and must state that identity/auth data can overwrite security-relevant state.
- Blocked tables may still appear in preview and final results summaries when other selected tables proceed successfully.

## Preview and Execution State Rules

- `inspection_id` and `run_id` are short-lived server-side workflow identifiers and must expire after a bounded server-controlled interval.
- Expired or abandoned inspection and preview state must be deleted after success, terminal failure, or abandonment.
- Execution must not start from a stale preview when the current environment has changed in a way that invalidates the preview assumptions.
- The workflow enforces single-run protection rather than queuing multiple concurrent partial restores.

## Audit Event Contract

The workflow must emit structured events via the existing audit system.

### Suggested event types
- `admin.partial_restore.inspect`
- `admin.partial_restore.preview`
- `admin.partial_restore.execute`
- `admin.partial_restore.complete`
- `admin.partial_restore.failed`

### Required payload fields
- `backup_filename`
- `backend`
- `source_format`
- `selected_tables`
- `required_groups`
- `skipped_conflict_counts`
- `table_outcomes`
- `result_summary`
- `warnings`
