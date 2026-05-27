# Data Model: Partial Backup Restore

## Overview

The feature does not require new persistent database tables in v1. Its main data model consists of request-scoped and temporary workflow objects layered over existing application tables and the existing `AuditLog` model.

## Entities

### BackupInspection

Represents the parsed metadata for one uploaded or selected backup during the admin workflow.

**Fields**
- `inspection_id`: Opaque identifier used to load the inspection state across requests.
- `backup_filename`: Original uploaded or selected backup filename.
- `backend`: `sqlite` or `postgresql`.
- `source_format`: `db.gz`, `db.gz.enc`, `sql.gz`, or `sql.gz.enc`.
- `encrypted`: Boolean indicating whether the source backup required decryption.
- `inspected_at`: UTC timestamp of inspection.
- `expires_at`: UTC timestamp after which the inspection state must not be used for execution.
- `table_summaries`: Collection of `RestorableTable` entries discovered in the backup.
- `parse_warnings`: Non-fatal warnings shown to the admin before selection.
- `full_restore_only`: Boolean flag used when the backup cannot support partial restore.

**Relationships**
- Has many `RestorableTable` records.
- May reference one or more `RequiredRestoreGroup` entries.

**Validation rules**
- Must resolve to exactly one supported backend.
- Must not proceed to preview when `full_restore_only` is true.
- Must not proceed to execution after `expires_at` without a fresh inspection and preview.
- Must keep backup metadata consistent with the decrypted/decompressed artifact actually inspected.

### RestorableTable

Represents one selectable table from the backup.

**Fields**
- `table_name`: Canonical database table name.
- `display_name`: UI label, initially matching table name.
- `row_count_estimate`: Estimated or exact row count from inspection.
- `row_count_kind`: `exact` or `estimate` to show preview confidence.
- `primary_key_columns`: Ordered list of primary-key column names when detectable.
- `sensitivity`: `normal` or `identity_sensitive`.
- `selected_by_default`: Boolean default for the selection UI.
- `required_group_key`: Optional reference to a `RequiredRestoreGroup`.
- `dependency_policy`: `explicit_only`, `auto_include`, or `block_if_missing`.
- `dependencies`: List of dependent table names required for a valid restore.
- `conflict_summary`: Optional `RestoreConflictSummary` populated during preview.

**Relationships**
- Belongs to one `BackupInspection`.
- May belong to one `RequiredRestoreGroup`.
- May have one `RestoreConflictSummary` in preview/execution flows.

**Validation rules**
- Sensitive identity tables must start with `selected_by_default = false`.
- `users` must always carry the identity restore-group key.
- Duplicate table names within one inspection are invalid.
- `dependency_policy = auto_include` is valid only for supported same-scope dependencies that can be previewed before execution.

### RequiredRestoreGroup

Represents a fixed set of tables that must be restored together.

**Fields**
- `group_key`: Stable identifier such as `identity_auth`.
- `display_name`: Human-readable label shown in the UI.
- `table_names`: Ordered list of required member tables.
- `excluded_tables`: Ordered list of related but non-auto-included tables such as `scim_tokens` and audit-log tables.
- `reason`: Explanation shown when a partial selection is invalid.

**Relationships**
- Applies to many `RestorableTable` entries.

**Validation rules**
- If any table in the group is selected, all tables in the group must be selected.
- Group membership must be derived from real schema dependencies, not user input.

### RestoreConflictSummary

Represents the preview-time conflict analysis for one selected table.

**Fields**
- `table_name`: Target table name.
- `backup_row_count`: Number of rows available in the backup for the table.
- `existing_row_count`: Number of rows currently present in the live database.
- `conflicting_row_count`: Number of rows that match existing primary keys.
- `importable_row_count`: Number of rows eligible for import under the default strategy.
- `conflict_key_kind`: `single_primary_key`, `composite_primary_key`, or `undetectable`.
- `strategy`: `skip_existing` in v1.
- `blocked_reason`: Optional explanation when the table cannot proceed.

**Validation rules**
- `conflicting_row_count + importable_row_count` must not exceed `backup_row_count`.
- `strategy` must stay aligned with the spec decision for v1.
- `blocked_reason` is required when `conflict_key_kind` is `undetectable`.

### PartialRestoreRun

Represents a single execution of the partial restore workflow.

**Fields**
- `run_id`: Opaque identifier for result lookup and audit correlation.
- `inspection_id`: Source inspection reference.
- `initiated_by_user_id`: Admin user who executed the restore.
- `selected_tables`: Final table selection submitted for restore.
- `started_at`: UTC timestamp.
- `completed_at`: UTC timestamp, optional until finish.
- `revalidated_at`: UTC timestamp capturing the pre-execution freshness check.
- `status`: `previewed`, `running`, `completed`, `partial`, `failed`, or `blocked`.
- `table_results`: Collection of `TableRestoreResult` entries.
- `warnings`: Collected warnings surfaced to the admin.

**Relationships**
- Has many `TableRestoreResult` entries.
- Emits one or more audit events through the existing `AuditLog` model.

**Validation rules**
- Cannot enter `running` without at least one selected table.
- Cannot include `users` without the full identity/auth required group.
- Must reject duplicate table names in `selected_tables` before execution begins.
- Must not enter `running` if a newer conflicting partial-restore run is already active for the same environment.
- Re-running the same selection against already restored rows must preserve `skip_existing` semantics rather than duplicating imported data.
- Must preserve the selected-table order or an explicit dependency order used for execution.

### TableRestoreResult

Represents the per-table outcome captured after execution.

**Fields**
- `table_name`: Restored table name.
- `status`: `restored`, `skipped`, `blocked`, or `failed`.
- `restored_row_count`: Rows imported successfully.
- `skipped_conflict_count`: Rows skipped because they already existed.
- `blocked_reason`: Optional explanation for blocked tables.
- `error_message`: Optional execution failure detail suitable for admin review.

**Validation rules**
- `restored_row_count` must be zero when status is `blocked` or `failed`.
- `blocked_reason` is required when status is `blocked`.

## State Transitions

### BackupInspection

`uploaded` → `inspected` → `previewable`

Alternate paths:
- `uploaded` → `full_restore_only`
- `uploaded` → `failed`

### PartialRestoreRun

`previewed` → `running` → `completed`

Alternate paths:
- `previewed` → `blocked`
- `running` → `partial`
- `running` → `failed`

## Existing Persistent Models Reused

- `AuditLog`: stores restore lifecycle events and structured result payloads.
- Identity models in `scaffold/apps/identity/models.py`: define the required `users` restore group (`roles`, `user_roles`, `aad_group_mappings`, `mfa_settings`, `passkey_credentials`).
