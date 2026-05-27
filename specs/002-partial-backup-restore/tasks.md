# Tasks: Partial Backup Restore

**Input**: Design documents from `/specs/002-partial-backup-restore/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Include test tasks whenever the feature changes behavior, security,
data flow, or schema. Omit them only when the work is strictly documentation or
non-executable project metadata.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., [US1], [US2], [US3])
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the feature-specific scaffolding and documentation targets used across all stories.

- [X] T001 Add partial-restore translation placeholders in scaffold/translations/en.json and scaffold/translations/nl.json
- [X] T002 Add partial-restore template placeholders in scaffold/apps/admin/templates/admin/partial_restore.html, scaffold/apps/admin/templates/admin/partial_restore_preview.html, and scaffold/apps/admin/templates/admin/partial_restore_results.html
- [X] T003 [P] Add feature-specific test module scaffold in tests/test_admin_partial_restore.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Extend scaffold/apps/admin/backup_utils.py with backup inspection helpers for SQLite and PostgreSQL table discovery
- [X] T005 [P] Define ephemeral workflow data structures and validation helpers in scaffold/apps/admin/backup_utils.py for BackupInspection, RestorableTable, RequiredRestoreGroup, RestoreConflictSummary, PartialRestoreRun, and TableRestoreResult
- [X] T006 [P] Add identity/auth restore-group definitions and dependency rules in scaffold/apps/admin/backup_utils.py using scaffold/apps/identity/models.py and scaffold/apps/scim/models.py as the schema reference
- [X] T007 Add admin partial-restore form classes and shared validation in scaffold/apps/admin/forms.py
- [X] T008 Add admin route skeletons and fresh-login/admin guards for partial restore in scaffold/apps/admin/routes.py
- [X] T009 [P] Add shared audit event helpers for partial-restore inspect, preview, execute, complete, and failed flows in scaffold/apps/admin/routes.py and scaffold/core/audit.py usage sites
- [X] T037 [P] Add explicit partial-restore eligibility rules for `.db.gz`, `.db.gz.enc`, `.sql.gz`, and `.sql.gz.enc`, plus full-restore-only classification for `.dump`, `.dump.gz`, malformed SQL dumps, and unreadable SQLite backups in scaffold/apps/admin/backup_utils.py
- [X] T038 Add selection normalization and deduplication for `selected_tables[]` submissions in scaffold/apps/admin/forms.py and scaffold/apps/admin/routes.py
- [X] T039 Add ephemeral preview/run expiry, execute-time revalidation, cleanup, and single-run concurrency guards in scaffold/apps/admin/backup_utils.py and scaffold/apps/admin/routes.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Restore selected tables from a backup (Priority: P1) 🎯 MVP

**Goal**: Allow an administrator to inspect a backup, select tables, and restore only that chosen scope while preserving unrelated current data.

**Independent Test**: Upload a supported backup through the admin workflow, select a small non-identity table set, execute the partial restore, and confirm only those selected tables change while unrelated tables remain unchanged.

### Tests for User Story 1 ⚠️

- [X] T010 [P] [US1] Add SQLite and PostgreSQL inspection helper tests in tests/test_admin_partial_restore.py
- [X] T011 [P] [US1] Add admin route integration test for inspect and table-selection flow in tests/test_admin_partial_restore.py
- [X] T012 [P] [US1] Add admin route integration test that restores only selected non-identity tables in tests/test_admin_partial_restore.py
- [X] T040 [P] [US1] Add failure-path tests for unsupported file variants, unreadable SQLite backups, and malformed PostgreSQL `.sql.gz` dumps in tests/test_admin_partial_restore.py
- [X] T043 [P] [US1] Add tests for schema-mismatch detection and blocking tables without a reliable conflict key in tests/test_admin_partial_restore.py

### Implementation for User Story 1

- [X] T013 [US1] Implement backup upload, decrypt, decompress, and inspection flow in scaffold/apps/admin/routes.py using scaffold/apps/admin/backup_utils.py
- [X] T014 [P] [US1] Implement supported-table selection UI in scaffold/apps/admin/templates/admin/partial_restore.html and scaffold/apps/admin/forms.py
- [X] T015 [US1] Implement backend-specific partial import helpers for selected non-identity tables in scaffold/apps/admin/backup_utils.py
- [X] T016 [US1] Wire the partial-restore inspect and execute routes into scaffold/apps/admin/routes.py and scaffold/apps/admin/templates/admin/backup.html
- [X] T017 [US1] Add user-facing copy for inspect, selection, unsupported-backup fallback, and restore success/error states in scaffold/translations/en.json and scaffold/translations/nl.json

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Understand restore impact before applying changes (Priority: P2)

**Goal**: Show dependency and conflict impact before execution so the administrator can make an informed restore decision.

**Independent Test**: Select tables that include dependency rules and existing-row conflicts, preview the restore, and verify the workflow shows required restore groups, blocked selections, and skip-existing conflict counts before execution.

### Tests for User Story 2 ⚠️

- [X] T018 [P] [US2] Add tests for required restore-group expansion and invalid identity-table selection in tests/test_admin_partial_restore.py
- [X] T019 [P] [US2] Add tests for conflict-summary generation and skip-existing preview behavior in tests/test_admin_partial_restore.py
- [X] T020 [P] [US2] Add admin route integration test for preview and blocked-selection messaging in tests/test_admin_partial_restore.py
- [X] T041 [P] [US2] Add tests for duplicate table selection collapse, stale preview rejection, and preview-expiry revalidation in tests/test_admin_partial_restore.py
- [X] T044 [P] [US2] Add tests for composite-key conflict detection, dependency auto-inclusion disclosure, and blocked cross-scope dependencies in tests/test_admin_partial_restore.py
- [X] T045 [P] [US2] Add tests for repeat-run idempotence under skip-existing behavior in tests/test_admin_partial_restore.py

### Implementation for User Story 2

- [X] T021 [US2] Implement dependency analysis, required restore-group expansion, and blocked-selection validation in scaffold/apps/admin/backup_utils.py
- [X] T022 [US2] Implement conflict-summary generation for selected tables in scaffold/apps/admin/backup_utils.py
- [X] T023 [US2] Implement preview route handling and preview-state orchestration in scaffold/apps/admin/routes.py
- [X] T024 [P] [US2] Implement preview UI for selected tables, conflict counts, dependency warnings, and sensitive-table acknowledgements in scaffold/apps/admin/templates/admin/partial_restore_preview.html
- [X] T025 [US2] Add preview-specific translations for warnings, blocked states, conflict summaries, and identity-group prompts in scaffold/translations/en.json and scaffold/translations/nl.json

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently.

---

## Phase 5: User Story 3 - Track and review partial restore outcomes (Priority: P3)

**Goal**: Record and present auditable per-table outcomes for partial restore attempts.

**Independent Test**: Complete a partial restore and verify that the results page and admin audit trail show actor, source backup, selected tables, and per-table restored/skipped/blocked/failed outcomes.

### Tests for User Story 3 ⚠️

- [X] T026 [P] [US3] Add tests for partial-restore audit event payloads in tests/test_admin_partial_restore.py
- [X] T027 [P] [US3] Add tests for per-table result summaries and failed/partial outcomes in tests/test_admin_partial_restore.py
- [X] T028 [P] [US3] Add admin route integration test for the partial-restore results page in tests/test_admin_partial_restore.py

### Implementation for User Story 3

- [X] T029 [US3] Implement partial-restore execution result tracking and per-table outcome assembly in scaffold/apps/admin/backup_utils.py and scaffold/apps/admin/routes.py
- [X] T030 [US3] Implement audit logging for inspect, preview, execute, complete, and failed events in scaffold/apps/admin/routes.py using scaffold/core/audit.py
- [X] T031 [P] [US3] Implement results page rendering for restored, skipped, blocked, and failed tables in scaffold/apps/admin/templates/admin/partial_restore_results.html
- [X] T032 [US3] Add results-page and audit-trail translations in scaffold/translations/en.json and scaffold/translations/nl.json

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories.

- [X] T033 [P] Document partial-restore operator workflow and fallback behavior in docs/deployment.md and docs/backup_encryption_plan.md
- [X] T034 [P] Add release-note or change-history coverage for partial restore in docs/history.md
- [X] T035 Validate the quickstart scenarios in specs/002-partial-backup-restore/quickstart.md and capture any required follow-up fixes in specs/002-partial-backup-restore/tasks.md
- [X] T036 Run focused regression coverage for admin backup/restore behavior with poetry run pytest tests/test_admin_routes.py tests/test_admin_partial_restore.py
- [X] T042 [P] Document preview-expiry, cleanup, and single-run concurrency behavior in docs/deployment.md and docs/backup_encryption_plan.md
- [X] T046 [P] Add backend-specific failure, dependency-state, schema-mismatch, and row-count estimate translations in scaffold/translations/en.json and scaffold/translations/nl.json
- [X] T047 [P] Document the timed validation fixture envelope and backup-generation dependency assumptions in docs/deployment.md and docs/backup_encryption_plan.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational phase completion.
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories.
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Depends on US1 selection and inspection flow surfaces but remains independently testable through preview.
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Depends on execution surfaces from US1/US2 but remains independently testable through results and audit review.

### Within Each User Story

- Tests for behavior, security, and data-flow changes MUST be written or updated before implementation completes.
- Inspection and validation helpers before route orchestration.
- Route orchestration before template completion.
- Core implementation before documentation and translation polish.
- Story complete before moving to the next priority when following MVP order.

### Parallel Opportunities

- T003 can run in parallel with T001-T002.
- T005, T006, and T009 can run in parallel after T004 begins the backup utility slice.
- Within US1, T010-T012 can run in parallel, and T014 can run in parallel with T013/T015 once forms exist.
- Within US2, T018-T020 can run in parallel, and T024-T025 can run in parallel after T023 defines preview data.
- Within US3, T026-T028 can run in parallel, and T031-T032 can run in parallel after T029-T030 define result payloads.
- T033 and T034 can run in parallel during polish.

---

## Parallel Example: User Story 1

```bash
# Launch User Story 1 tests together:
Task: "Add SQLite and PostgreSQL inspection helper tests in tests/test_admin_partial_restore.py"
Task: "Add admin route integration test for inspect and table-selection flow in tests/test_admin_partial_restore.py"
Task: "Add admin route integration test that restores only selected non-identity tables in tests/test_admin_partial_restore.py"

# Launch compatible implementation tasks together:
Task: "Implement supported-table selection UI in scaffold/apps/admin/templates/admin/partial_restore.html and scaffold/apps/admin/forms.py"
Task: "Implement backend-specific partial import helpers for selected non-identity tables in scaffold/apps/admin/backup_utils.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: Test User Story 1 independently.
5. Demo or ship the minimum partial-restore flow for selected non-identity tables.

### Incremental Delivery

1. Complete Setup + Foundational → foundation ready.
2. Add User Story 1 → test independently → demo MVP.
3. Add User Story 2 → test preview/dependency/conflict handling independently → demo.
4. Add User Story 3 → test results and audit visibility independently → demo.
5. Finish polish docs and regression validation.

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together.
2. Once Foundational is done:
   - Developer A: User Story 1 routes, execution helpers, and base UI.
   - Developer B: User Story 2 preview/dependency/conflict logic.
   - Developer C: User Story 3 audit/results flow and docs updates.
3. Integrate after each story-level checkpoint.

---

## Notes

- [P] tasks = different files, no dependencies.
- [US1], [US2], [US3] labels map tasks to specific user stories for traceability.
- Each user story is independently completable and testable.
- No Alembic migration task is included because the plan explicitly keeps preview/run state ephemeral in v1.
- Full restore remains a fallback path and is covered through docs and regression validation rather than a new user-story phase.
