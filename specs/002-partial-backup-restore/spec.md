# Feature Specification: Partial Backup Restore

**Feature Branch**: `[002-partial-backup-restore]`

**Created**: 2026-05-27

**Status**: Draft

**Input**: User description: "partial restores from backup in webinterface"

## Clarifications

### Session 2026-05-27

- Q: Which table-selection policy should partial restore use? → A: Allow any table, including `user`, but require strong warnings.
- Q: How should conflicts behave when selected tables already have current data? → A: Skip conflicting existing rows by default and import only non-conflicting rows.
- Q: How should the UI treat sensitive tables such as `user` by default? → A: Show all tables, but keep `user` and related identity tables deselected by default and require explicit selection.
- Q: How should `user` and related identity/auth tables be restored? → A: Treat `user` and related identity/auth tables as a required restore group that must be selected together.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Restore selected tables from a backup (Priority: P1)

An administrator can open a backup in the web interface, review which database tables it contains, and restore only the selected tables into the current environment instead of replacing the whole application dataset.

**Why this priority**: The core user value is recovering a limited scope of lost or damaged business data without undoing unrelated work that happened after the backup was created.

**Independent Test**: Can be fully tested by uploading or selecting an eligible backup, choosing a small set of tables, completing the restore, and confirming those tables are recovered while unrelated current tables remain unchanged.

**Acceptance Scenarios**:

1. **Given** an administrator has access to a supported backup, **When** they open the partial restore workflow, **Then** they can see the available tables in a way that makes selective recovery possible, with sensitive identity tables shown but not preselected.
2. **Given** an administrator selects one or more tables from a backup, **When** they confirm the restore, **Then** only the selected tables and their required dependent data are restored into the current environment, including any required table groups.

---

### User Story 2 - Understand restore impact before applying changes (Priority: P2)

An administrator can review what table data will be created, updated, skipped, or blocked before running a partial restore so they can avoid accidental overwrites and resolve conflicts deliberately.

**Why this priority**: Partial recovery is high-risk administrative work. Users need clear impact information before making changes to production data.

**Independent Test**: Can be fully tested by selecting backup tables that conflict with current data and verifying that the workflow explains the impact and allows the administrator to proceed only with an informed decision.

**Acceptance Scenarios**:

1. **Given** a selected backup table would conflict with existing current data, **When** the administrator reviews the partial restore plan, **Then** the workflow identifies the conflict and explains that conflicting existing rows will be skipped by default while non-conflicting rows can still be imported.
2. **Given** a selected backup table depends on related records or required table groups that are also necessary for a valid restore, **When** the administrator reviews the restore plan, **Then** the workflow shows those dependencies before the restore is confirmed.

---

### User Story 3 - Track and review partial restore outcomes (Priority: P3)

An administrator can review the result of a partial restore, including which selected tables succeeded, failed, or were skipped, so the organization has a reliable recovery record and can complete any follow-up actions.

**Why this priority**: Recovery tasks need accountability. Administrators must be able to prove what changed and identify any remaining manual work.

**Independent Test**: Can be fully tested by completing a partial restore and confirming that the workflow records the actor, source backup, selected tables, and per-table outcome for later review.

**Acceptance Scenarios**:

1. **Given** a partial restore finishes successfully or partially successfully, **When** the administrator views the result, **Then** they can see which selected tables were restored, skipped, or failed.
2. **Given** a partial restore changes application data, **When** an auditor or administrator reviews the event history, **Then** the restore actor, timing, backup source, and affected items are available for review.

---

### Edge Cases

- If a backup cannot be inspected for selective recovery, the workflow prevents partial restore and explains that only full restore remains available for that backup.
- If selected tables rely on related records that are missing, incompatible, or outside the supported partial-restore scope, the workflow blocks or skips those tables with a clear reason.
- If a selected table already exists in the current environment and cannot be safely merged, the workflow requires an explicit conflict decision before continuing.
- If an administrator selects no eligible items, the workflow does not start a partial restore.
- If the restore is interrupted partway through, the workflow records which items completed and which did not, so administrators can assess follow-up actions.
- If an administrator selects highly sensitive tables such as `user`, the workflow displays strong warnings before the restore is confirmed.
- If a backup contains sensitive identity tables such as `user`, those tables appear deselected by default and require explicit administrator selection before they can be restored.
- If an administrator selects `user`, the workflow requires selection of the associated identity/auth restore group and does not allow `user` to be restored as a standalone table.
- If the same partial restore is repeated after a prior successful or partial run, the workflow reports already-imported conflicting rows as skipped rather than restoring them again.
- If a selected table exists in the backup but not in the current schema, or lacks a reliable conflict key, the workflow blocks that table before execution and explains why full restore or manual recovery is required.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide an administrator-facing web workflow for partial restore from a supported backup source.
- **FR-002**: The system MUST allow administrators to inspect the available tables in a backup before confirming a partial restore.
- **FR-003**: The system MUST present restorable tables in clearly labeled groups so administrators can select a subset for recovery.
- **FR-004**: The system MUST restore only the selected tables and the minimum dependent records required to keep those tables usable after recovery.
- **FR-005**: The system MUST preserve current records that are outside the selected restore scope.
- **FR-006**: The system MUST show, before confirmation, which selected tables are expected to be created, updated, skipped, blocked, or require a conflict decision.
- **FR-007**: The system MUST prevent a partial restore from starting when no eligible items are selected.
- **FR-008**: The system MUST block or clearly exclude backup content that is not supported for partial restore, while leaving full restore available as a separate recovery path when applicable.
- **FR-009**: The system MUST enforce the same or stricter administrative permission checks for partial restore as for full backup and restore actions.
- **FR-010**: The system MUST record an audit trail for each partial restore attempt, including actor, time, backup source, selected tables, and outcome.
- **FR-011**: The system MUST provide administrators with a result summary that distinguishes restored, skipped, blocked, and failed tables.
- **FR-012**: The system MUST prevent duplicate or repeated selection entries from causing the same table to be restored more than once in a single partial restore operation.
- **FR-013**: The system MUST preserve referential consistency for restored tables, either by restoring required dependencies automatically or by blocking the selection with a clear explanation.
- **FR-014**: The system MUST inform administrators when backup content is incompatible with the current environment or feature scope before any partial restore changes are applied.
- **FR-015**: The system MUST allow selection of any backed-up table, including the `user` table, during partial restore.
- **FR-016**: The system MUST present strong warnings before restoring highly sensitive tables, including `user` and related identity data.
- **FR-017**: When selected tables contain rows that conflict with existing current data, the system MUST skip conflicting rows by default and import only non-conflicting rows unless the restore is blocked for another reason.
- **FR-018**: The system MUST show sensitive identity tables, including `user` and related identity tables, as deselected by default and require explicit administrator selection before including them in a partial restore.
- **FR-019**: The system MUST treat `user` and its related identity/auth tables as a required restore group and MUST not allow `user` to be restored without the other tables required for a valid identity state.
- **FR-020**: Partial restore MUST support only these backup source variants in v1: SQLite `.db.gz`, SQLite `.db.gz.enc`, PostgreSQL plain dump `.sql.gz`, and PostgreSQL plain dump `.sql.gz.enc`.
- **FR-021**: The required identity/auth restore group for `user` MUST include exactly `users`, `roles`, `user_roles`, `aad_group_mappings`, `mfa_settings`, and `passkey_credentials`.
- **FR-022**: `scim_tokens`, audit-log tables, and other security-adjacent tables MUST NOT be auto-included in the `user` identity/auth restore group and remain separately selectable only when they are supported by the partial-restore eligibility rules.
- **FR-023**: Preview and execution state for a partial restore MUST expire after a bounded server-controlled interval, MUST be revalidated against the current environment before execution, and MUST be deleted after success, terminal failure, or user abandonment.
- **FR-024**: The system MUST prevent concurrent partial-restore executions against the same environment, either by blocking a second run until the active run completes or by enforcing an equivalent single-run guard.
- **FR-025**: The system MUST classify non-identity dependencies for each selected table as either preview-disclosed auto-included dependencies or blocking dependencies before execution begins.
- **FR-026**: The system MUST auto-include only supported same-scope dependency tables that are present in the backup and required to preserve referential integrity; cross-domain, security-adjacent, missing, or partially present dependencies MUST block the affected selection instead of being silently imported.
- **FR-027**: Conflict detection MUST use the full primary-key tuple for composite primary keys, the declared primary-key value for single-column keys, and MUST block table-level partial restore when no reliable conflict key can be determined.
- **FR-028**: Repeating the same partial restore against rows already imported by an earlier run MUST be idempotent under the default skip-existing strategy and MUST report those rows as skipped conflicts instead of restoring them again.
- **FR-029**: If a selected table exists in the backup but not in the current schema, exists in the current schema but not in the backup, or is otherwise outside the inspected partial-restore scope, the workflow MUST mark that table as unavailable or blocked before execution and explain the schema mismatch.
- **FR-030**: The system MUST localize inspect, preview, execute, and results copy for backend-specific parse or decryption failures, dependency warnings, conflict summaries, row-count estimate labels, schema-mismatch messages, and result-state labels.
- **FR-031**: Partial-restore eligibility MUST remain coupled to the current backup-generation behavior for supported SQLite and PostgreSQL exports; any new or changed backup format MUST default to full-restore-only until the eligibility rules are updated.

### Supported Backup Eligibility

- **SQLite partial-restore eligible**: `.db.gz`, `.db.gz.enc`
- **PostgreSQL partial-restore eligible**: `.sql.gz`, `.sql.gz.enc` when the dump is parseable as a plain `pg_dump --format=plain --no-owner --no-privileges` SQL export
- **Full-restore-only in v1**: `.dump`, `.dump.gz`, malformed SQL dumps, unreadable SQLite backups, and any backup whose structure cannot be inspected safely for table-level restore
- **Incompatible content handling**: When a backup is encrypted with an unusable key, malformed, unreadable, or otherwise not inspectable, the workflow must stop before preview and present full-restore-only guidance rather than attempting a best-effort partial restore

### Dependency And Conflict Policy

- **Explicit administrator selection**: The selected restore scope starts with the tables explicitly chosen by the administrator after duplicate selections are normalized away.
- **Preview-disclosed auto-included dependencies**: The workflow may add same-scope lookup tables, join tables, or other directly required support tables only when they are present in the inspected backup, are supported for partial restore, and can be identified before execution. Every auto-included table must appear in preview and results as dependency-added scope.
- **Blocking dependencies**: Dependencies that are cross-domain, security-adjacent, only partially available, missing from the backup, missing from the current schema, or otherwise outside supported table-level restore scope must block the affected selection with a clear explanation instead of being imported implicitly.
- **Conflict identity rules**: Preview and execution must compare rows using the full primary-key tuple for composite keys and the single declared primary-key value for single-column keys. Tables without a detectable primary key or equivalent stable conflict key are blocked from partial restore in v1.
- **Repeat-run behavior**: A second run using the same backup content and selected scope must preserve the existing skip-conflict default by treating already imported matching rows as skipped conflicts rather than as fresh restores.

### Key Entities *(include if feature involves data)*

- **Backup Snapshot**: A recoverable backup source that contains business records, metadata, and identifying information about when the backup was created.
- **Restorable Table**: A selectable database table from a backup that can be recovered independently or with required dependencies.
- **Selected Restore Scope**: The final execution scope consisting of administrator-selected tables plus any preview-disclosed auto-included dependencies.
- **Required Restore Group**: A fixed set of related tables that must be selected and restored together to preserve a valid application state, such as the `user` identity/auth group of `users`, `roles`, `user_roles`, `aad_group_mappings`, `mfa_settings`, and `passkey_credentials`.
- **Restore Dependency**: A related record or table that must also exist or be restored for a selected table to remain valid and usable.
- **Restore Conflict**: A condition where backup content overlaps with current environment data and requires a defined outcome such as create, update, skip, or block.
- **Partial Restore Event**: A recorded recovery action that captures who initiated it, from which backup, with what scope, and with what result.

## Security, Audit, and Operations *(mandatory)*

- **Authorization Impact**: Partial restore is limited to administrators or an equivalent existing privileged role already trusted with backup and restore actions; ordinary assessment users do not gain new recovery access.
- **Audit/Event Impact**: Every partial restore attempt must capture actor, source backup, selected tables, start and end time, and table-level outcomes that can be reviewed later.
- **Data Sensitivity Impact**: Backup inspection and selective recovery may expose sensitive assessment content, risk information, user identities, and authentication-related data, so the workflow must protect visibility and recovery actions with existing high-trust administrative controls, prominent warnings for sensitive table restores, and safe default deselection of identity tables.
- **Migration/Backfill Impact**: No historical data backfill is required for existing backups, but unsupported or older backup formats may need to be explicitly marked as full-restore-only.
- **Localization Impact**: New workflow labels, warnings, backend-specific parse and decryption failures, conflict explanations, row-count estimate labels, schema-mismatch messages, and outcome summaries require translation support.
- **Deployment/Configuration Impact**: Operational guidance must define which backup formats and content groups are eligible for partial restore, identify required restore groups such as the identity/auth group, define preview-expiry and cleanup behavior, describe single-run concurrency protection, describe the supported validation envelope for timed admin recovery tasks, and provide a clear recovery runbook for conflict handling, schema mismatch handling, and post-restore verification.

## Success Criteria *(mandatory)*

### Validation Baseline

- **Representative timed fixture**: SC-001 is measured from the start of `GET /admin/backup/partial-restore` using approved SQLite `.db.gz` and PostgreSQL `.sql.gz` validation fixtures that expose 10 to 20 restorable tables and require a valid 3-table non-identity selection.
- **Protected data definition**: For SC-002, "unrelated current records" means rows in tables outside the final selected restore scope and outside any preview-disclosed auto-included dependency tables.
- **Supported-attempt denominator**: For SC-004, "supported partial restore attempts" means the approved validation matrix of partial-restore-eligible SQLite and PostgreSQL fixtures, excluding malformed, unreadable, encrypted-without-key, and full-restore-only backups.
- **Performance envelope assumption**: Validation for SC-001 and SC-004 assumes operator-run backups that stay within the approved timed-fixture envelope above; larger or future backup variants may remain operationally valid but are outside the v1 timed success target until explicitly added.

### Measurable Outcomes

- **SC-001**: In at least 90% of timed validation runs using the representative timed fixture, administrators can inspect the backup and submit a valid restore selection in under 5 minutes from the start of the partial-restore entry workflow.
- **SC-002**: In 100% of approved validation scenarios, executing a partial restore changes only rows in the final selected restore scope and leaves all unrelated current records unchanged.
- **SC-003**: 100% of partial restore attempts produce a reviewable audit record with actor, backup source, selected scope, and outcome.
- **SC-004**: At least 90% of supported partial restore attempts in the approved validation matrix complete without requiring operator fallback to full restore.
- **SC-005**: Administrators can determine, from the result summary alone, which selected tables succeeded, failed, or were skipped in 100% of tested restore runs.

## Assumptions

- Partial restore is intended for high-trust administrative recovery work performed through the existing backup and restore area of the web interface.
- The first release targets table-level selective recovery rather than row-level recovery.
- Full restore remains available for backups or content types that cannot be safely inspected or selectively reapplied.
- Restored tables may belong to multiple domain modules, including identity-related tables when explicitly selected by an administrator.
- Existing audit, localization, and administrative access patterns will be reused for this feature.
- Sensitive identity tables are visible in the selection UI, but they are not preselected and require explicit administrator opt-in.
- The `user` table cannot be restored safely on its own and therefore must be restored together with its required identity/auth table group.
- Preview state is short-lived server-side workflow state rather than a persistent application record and must be revalidated before execution.
- Supported partial restore remains aligned to the backup variants currently generated by the application; future backup-format changes are treated as full-restore-only until the eligibility matrix is revised.
