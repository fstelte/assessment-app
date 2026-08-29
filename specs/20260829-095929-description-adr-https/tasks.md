---
feature: 20260829-095929-description-adr-https
status: planned
created: 2026-08-29
chunk_size: medium
total_tasks: 12
estimated_lines: 735
---

# Architecture Decision Records on the SSP — Tasks

## Overview
Implements the Architecture Principle catalogue (admin CRUD + bulk import) and ADR
records on System Security Plans, per `design.md` and decision records
`20260829-1011-adr-principle-catalogue-design` and
`20260829-1011-principle-bulk-import-format`.

## Task List

### Foundation

#### Task 1: ArchitecturePrinciple model + migration
- **Estimate:** ~50 lines
- **Files:** `scaffold/apps/ssp/models.py`, `migrations/versions/`
- **Description:** Add `ArchitecturePrinciple` (`id`, `name` unique case-insensitive, `description`, `created_at`, `updated_at`, `TimestampMixin`) and its Alembic migration creating `architecture_principles`.
- **Depends on:** None
- **Acceptance:** Model importable, table created by `flask db upgrade`, unique constraint on `name` enforced.
- **Evidence:** Migration applies cleanly (`flask db upgrade` / `downgrade` round-trip); a quick shell insert of two same-name (case-varied) rows raises an integrity error.

#### Task 2: ADRRecord + ADRSecondaryPrinciple models + migration
- **Estimate:** ~85 lines
- **Files:** `scaffold/apps/ssp/models.py`, `migrations/versions/`
- **Description:** Add `ADRRecord` (`id`, `ssp_id` FK cascade delete, `title`, `status` enum per FR-007, `context`, `decision`, `consequences`, `primary_principle_id` FK NOT NULL, `supersedes_id` nullable self-FK, `author_id` FK, `decided_on`, timestamps), `ADRSecondaryPrinciple` association table (`adr_id`, `principle_id`), `back_populates` on `SSPlan`, plus the Alembic migration for `adr_records` and `adr_secondary_principles`.
- **Depends on:** Task 1
- **Acceptance:** Models importable, tables/constraints created, `SSPlan.adr_records` relationship works, cascade-delete on parent SSP delete verified.
- **Evidence:** Migration applies cleanly; deleting an `SSPlan` in a shell/test session cascades to its `ADRRecord` rows.

### Core Implementation — Principle admin (parallel to ADR track)

#### Task 3: Principle admin forms [P]
- **Estimate:** ~40 lines
- **Parallel:** Can run with Task 4, Task 7
- **Files:** `scaffold/apps/admin/forms.py`
- **Description:** `PrincipleCreateForm`, `PrincipleUpdateForm(PrincipleCreateForm)`, `PrincipleDeleteForm`, `PrincipleImportForm` (JSON-only `FileField`), mirroring `ControlCreateForm`/`ControlImportForm` (`scaffold/apps/admin/forms.py:21,34,60,67`), labels via `lazy_gettext` (FR-013).
- **Depends on:** Task 1
- **Acceptance:** Forms validate required `name`/`description`, import form rejects non-JSON uploads.
- **Evidence:** Form-level unit test or manual POST with a `.txt` file returns a validation error.

#### Task 4: `principle_importer.py` service [P]
- **Estimate:** ~55 lines
- **Parallel:** Can run with Task 3, Task 7
- **Files:** `scaffold/apps/ssp/principle_importer.py`
- **Description:** `upsert_principle()` (case-insensitive, trimmed, casefolded `name` match; overwrite `description` on match per FR-002), `import_principles_from_mapping(payload)` returning `ImportStats(created, updated, errors)`, duplicate-in-file handling, mirroring the mechanics (not payload shape) of `control_importer.py`.
- **Depends on:** Task 1
- **Acceptance:** Importing the example `principles.json` from `design.md` creates 4 principles; re-importing updates 4 and creates 0; a file with a duplicate name reports the earlier occurrence as superseded-within-file.
- **Evidence:** Unit test asserts `ImportStats.created == 4` on first run, `updated == 4` on second run.

#### Task 5: Principle admin routes
- **Estimate:** ~80 lines
- **Files:** `scaffold/apps/admin/routes.py`
- **Description:** `principles()` view at `/admin/principles` (GET/POST, paginated per FR-010) plus `/create`, `/<id>/edit` (GET), `/<id>/update` (POST), `/<id>/delete` (POST, enforces FR-003's use-guard), `/delete-bulk` (POST), file-upload wired to `principle_importer`, `_require_control_admin()`-style role check (FR-011), `log_event()` calls on create/update/delete/import (FR-012).
- **Depends on:** Task 3, Task 4
- **Acceptance:** Non-admin gets 403; admin can create/edit/delete a principle; deleting a principle referenced by an ADR is blocked with a message naming the blocking ADR(s); every mutating action writes an `AuditLog` row.
- **Evidence:** Route-level pytest covering the 403 case, the delete-guard case, and an `AuditLog` row existing after create.

#### Task 6: Principle admin templates
- **Estimate:** ~65 lines
- **Files:** `scaffold/apps/admin/templates/admin/principles*.html` (or equivalent existing template dir)
- **Description:** List (paginated, per FR-010), create/edit forms, import upload UI with created/updated/errors summary display. Tailwind, i18n via existing macros (Constitution Principle IV).
- **Depends on:** Task 5
- **Acceptance:** Page renders for an admin user; import summary is visible after upload; no Bootstrap introduced.
- **Evidence:** Manual render check in a running dev server; template lints/builds without errors.

### Core Implementation — ADR track

#### Task 7: ADR forms [P]
- **Estimate:** ~65 lines
- **Parallel:** Can run with Task 3, Task 4
- **Files:** `scaffold/apps/ssp/forms.py`
- **Description:** ADR create/edit form (title/status/context/decision/consequences), primary-principle picker (required, not editable on update per FR-004), secondary-principles multi-select, "supersedes" picker scoped to ADRs within the same SSP (FR-008). Labels via `lazy_gettext`.
- **Depends on:** Task 2
- **Acceptance:** Form rejects submission with no primary principle; update form has no field capable of changing `primary_principle_id`.
- **Evidence:** Unit test: submitting an update payload with a different `primary_principle_id` is ignored/rejected.

#### Task 8: ADR routes + supersession/delete-guard logic
- **Estimate:** ~85 lines
- **Files:** `scaffold/apps/ssp/routes.py`
- **Description:** Create/list/detail/status-transition routes for ADRs on an SSP; status-transition validation per FR-007's explicit table; on create-with-`supersedes`, flip the prior ADR to `Superseded` and reject if the target is out-of-SSP or already superseded (FR-008); reject principle delete requests when referenced (server-side half of FR-003, called from Task 5's delete route); `log_event()` on create and every status change (FR-012).
- **Depends on:** Task 7
- **Acceptance:** Invalid status transitions (e.g. `Rejected → Accepted`) are rejected; supersede flips the old ADR and both directions of the link resolve; cross-SSP supersede target is rejected.
- **Evidence:** Route-level pytest covering an invalid transition, a valid supersede, and a rejected cross-SSP supersede attempt.

#### Task 9: ADR templates
- **Estimate:** ~80 lines
- **Files:** `scaffold/apps/ssp/templates/ssp/`
- **Description:** New "ADRs" tab on the SSP detail view; list with status/principle filters (paginated per FR-010); create form (principle selection gates the rest, per FR-004/User Story 3); detail view showing supersession links both directions; empty-catalogue messaging per role (FR-014). Tailwind, i18n.
- **Depends on:** Task 8
- **Acceptance:** Tab renders on an SSP with ADRs; empty-principle-catalogue state shows the admin-only link only to admins.
- **Evidence:** Manual render check for both an admin and non-admin session against an SSP with zero principles.

### Integration & Polish

#### Task 10: Pytest — principle admin CRUD + import
- **Estimate:** ~55 lines
- **Files:** `tests/` (path matching existing admin test layout)
- **Description:** Covers upsert create/update counts, invalid-file rejection, partial-batch errors, delete-in-use guard, non-admin 403, audit-log rows written.
- **Depends on:** Task 5, Task 6
- **Acceptance:** All listed scenarios pass.
- **Evidence:** `pytest` run green for the new test module.

#### Task 11: Pytest — ADR creation + supersession + principle-delete guard
- **Estimate:** ~65 lines
- **Files:** `tests/` (path matching existing ssp test layout)
- **Description:** Covers principle-required-before-save, secondary principles persisted, invalid status transitions rejected, supersede flips status and both link directions resolve (backs SC-003), double-supersede rejected, cross-SSP supersede rejected, principle delete blocked while referenced then allowed after ADR removed.
- **Depends on:** Task 8, Task 9
- **Acceptance:** All listed scenarios pass.
- **Evidence:** `pytest` run green for the new test module.

#### Task 12: Docs update
- **Estimate:** ~25 lines
- **Files:** `README.md` or `docs/`
- **Description:** Document the new Architecture Principle admin catalogue, the bulk-import file format (with the `principles.json` example from `design.md`), and the ADR feature on SSPs, per Constitution Principle V (operational readiness) and the delivery-workflow doc requirement.
- **Depends on:** Task 6, Task 9 (describes finished UI)
- **Acceptance:** Docs describe the feature and link/reproduce the example import file.
- **Evidence:** Doc renders correctly; reviewer can follow it to perform an import without reading code.

## Notes
- Tasks 3, 4, and 7 touch disjoint files and can be worked in parallel once Tasks 1–2 land.
- FR-012 (audit logging) and FR-013 (localization) are cross-cutting requirements folded into Tasks 5, 6, 8, 9 rather than given standalone tasks — each implementation task's acceptance criteria include them.
- Deferred/out of scope (see `design.md` Open Questions): ADR export/print, soft-delete/archive for principles, concurrent-import conflict handling.

## Progress
- [x] Task 1: ArchitecturePrinciple model + migration
- [x] Task 2: ADRRecord + ADRSecondaryPrinciple models + migration
- [x] Task 3: Principle admin forms
- [x] Task 4: principle_importer.py service
- [x] Task 5: Principle admin routes
- [x] Task 6: Principle admin templates
- [x] Task 7: ADR forms
- [x] Task 8: ADR routes + supersession/delete-guard logic
- [x] Task 9: ADR templates
- [x] Task 10: Pytest — principle admin CRUD + import
- [ ] Task 11: Pytest — ADR creation + supersession + principle-delete guard
- [ ] Task 12: Docs update
