---
feature: authentication-mechanism-also-used-for-authorisation
status: planned
created: 2026-09-18
chunk_size: medium
total_tasks: 7
estimated_lines: 360
---

# Authentication Mechanism Also Used for Authorisation Tasks

## Overview

Implements the design in `design.md`: adds a `used_for_authorization`
boolean + `authorization_note` free-text field to `ComponentEnvironment`
(the same place the authentication mechanism is already identified per
environment), and surfaces it in the environment badge, the component
edit forms, and the authentication overview export.

## Task List

### Foundation

#### Task 1: Model & migration - add authorisation fields to ComponentEnvironment
- **Estimate:** ~70 lines
- **Files:** `scaffold/apps/bia/models/__init__.py`,
  `migrations/versions/<new>_bia_component_environment_authorization.py`
- **Description:** Add `used_for_authorization = db.Column(db.Boolean,
  nullable=False, default=False, server_default=sa.false())` and
  `authorization_note = db.Column(db.Text, nullable=True)` to
  `ComponentEnvironment` (models/__init__.py:204-235, table
  `bia_component_environments`). Add a new Alembic migration (follow the
  style of `migrations/versions/20251124_0011_bia_component_environments.py`)
  that adds both columns via `op.add_column` with `server_default=sa.false()`
  on the boolean column, and a downgrade that drops both columns.
  **Note:** this migration history currently has two heads
  (`20251205_0015` and `20260830_0001` — confirmed via down_revision
  analysis since `alembic heads` isn't runnable in this environment). Check
  which one is actually current in the target DB (or run `alembic heads`
  in an environment with alembic installed) before setting `down_revision`
  — do not assume either head from this list without verifying.
- **Depends on:** None
- **Acceptance:** `ComponentEnvironment` has both new attributes with
  correct defaults; migration upgrades and downgrades cleanly against the
  correct current head.
- **Evidence:** Migration runs (`flask db upgrade` / equivalent) without
  error against a fresh test DB; `pytest` model-level tests (if any) still
  pass.

#### Task 2: [P] Translations - authorisation field and column labels
- **Estimate:** ~30 lines (across 2 files)
- **Parallel:** Can run with Task 1, 3
- **Files:** `scaffold/translations/en.json`, `scaffold/translations/nl.json`
- **Description:** Add keys under `bia.components.environments` for the
  new checkbox label (e.g. `used_for_authorization`) and note field
  label/placeholder (e.g. `authorization_note_label`,
  `authorization_note_placeholder`), and under
  `bia.export.authentication_overview.columns` (e.g.
  `used_for_authorization`) and `.summary` (e.g.
  `used_for_authorization_count`) for the export column header and summary
  label, in both locale files, following existing key structure/naming.
- **Depends on:** None
- **Acceptance:** New keys resolve in both `en` and `nl` locales with no
  missing-translation fallback.
- **Evidence:** App starts without translation errors; keys render
  expected text in both locales.

### Core Implementation

#### Task 3: [P] Form & sync - capture the flag/note on save
- **Estimate:** ~40 lines
- **Parallel:** Can run with Task 4
- **Files:** `scaffold/apps/bia/forms.py`
- **Description:** Add `used_for_authorization = BooleanField(...)` and
  `authorization_note = StringField(...)` (or `TextAreaField`) to
  `ComponentEnvironmentForm` (forms.py:188-201), both `Optional()`. In
  `_sync_component_environments` (routes.py:269-296), set
  `environment.used_for_authorization = bool(subform.used_for_authorization.data)`
  and `environment.authorization_note = (subform.authorization_note.data or
  None)` alongside the existing `authentication_method_id` assignment
  (routes.py:287-288), for both the create-new-environment and
  update-existing-environment branches. Also populate these two fields when
  pre-filling the form for an existing environment (the block around
  routes.py:180-185 that sets `subform.is_enabled.data` /
  `subform.authentication_method.data` from `matched`).
- **Depends on:** Task 1
- **Acceptance:** Submitting the component create/edit form with the
  checkbox checked and a note persists both fields on the corresponding
  `ComponentEnvironment` row; re-opening the edit form shows the persisted
  values.
- **Evidence:** `pytest tests/test_bia_routes.py` (new/updated test from
  Task 7) passes; manual form round-trip.

#### Task 4: [P] Route - serialize the flag/note and resolve it per component
- **Estimate:** ~55 lines
- **Parallel:** Can run with Task 3
- **Files:** `scaffold/apps/bia/routes.py`
- **Description:** Extend `_serialize_environments` (routes.py:251-266) to
  include `used_for_authorization` and `authorization_note` keys per
  environment (read directly off the `ComponentEnvironment` row — no
  resolution needed there, each row owns its own values). Add a new
  `_resolve_component_authorization_usage(component: Component) -> tuple[bool,
  str | None]` helper next to `_resolve_component_authentication_method_id`
  (routes.py:203-217) that mirrors its fallback chain — it reads off
  `_select_primary_environment_assignment(component)` (routes.py:188-200)
  since the authorisation flag/note live only on `ComponentEnvironment`,
  not on the legacy `Component`-level override. Use this new helper in
  `export_authentication_overview` (routes.py:1720-1782) to compute a
  `used_for_authorization`/`authorization_note` pair per component,
  attached to each component row passed to the template (e.g. via a small
  per-component wrapper dict, matching how `groups`/`unassigned` are
  already built), and add a count of authorisation-flagged components to
  each `groups` entry AND to the `unassigned` list (as a separate
  `unassigned_authorization_count` value passed to the template) for the
  summary table's unassigned row.
- **Depends on:** Task 1
- **Acceptance:** `get_component`/create/update JSON responses include the
  new per-environment keys; the export route computes correct
  per-component resolved values and per-group counts for a mix of
  flagged/unflagged/no-environment components.
- **Evidence:** `pytest tests/test_bia_routes.py` (Task 7) passes.

### Integration & Polish

#### Task 5: [P] Templates - environment editor rows and badge
- **Estimate:** ~55 lines (across 2 files)
- **Parallel:** Can run with Task 6
- **Files:** `scaffold/apps/bia/templates/bia/components.html`,
  `scaffold/apps/bia/templates/bia/edit_component.html`
- **Description:** In both files' environment-row tables
  (components.html:191-217, edit_component.html:101-127), add a new
  `<th>`/`<td>` pair rendering
  `environment_field.form.used_for_authorization` (checkbox) and
  `environment_field.form.authorization_note` (text input, only
  meaningfully relevant when the checkbox is checked — no JS toggle
  required for this pass, per scope agreed in design). Update the badge
  `title` attribute in components.html:281 to append the authorisation
  status (e.g. append " · Also used for authorisation" when
  `env_data.used_for_authorization` is true), using the Task 2 translation
  key.
- **Depends on:** Task 1, Task 2, Task 3, Task 4
- **Acceptance:** Both environment editor tables show the new checkbox +
  note column; the environment badge title reflects the flag when set.
- **Evidence:** Manual render check of the add/edit component modal and
  the components list badge tooltip.

#### Task 6: [P] Export template - authorisation column and summary count
- **Estimate:** ~40 lines
- **Parallel:** Can run with Task 5
- **Files:** `scaffold/apps/bia/templates/bia/export_authentication.html`
- **Description:** Add an "Also used for authorisation" `<th>`/`<td>` pair
  to the per-method detail table (lines 103-121) and the unassigned table
  (lines 137-156), rendering a yes/no indicator per component (with the
  note, if present, as a `title` attribute on the cell). Add the
  authorisation-flagged count from Task 4 as a new column on the existing
  method-summary table (lines 26-53), including the "unassigned" row
  (lines 47-53) using `unassigned_authorization_count`.
- **Depends on:** Task 2, Task 4
- **Acceptance:** Export HTML shows the authorisation indicator per
  component row in both table types, and the correct flagged-count per
  method in the summary table.
- **Evidence:** Manual render check against seeded data with a mix of
  flagged/unflagged components across methods.

#### Task 7: Tests - cover persistence, serialization, and export rendering
- **Estimate:** ~70 lines
- **Files:** `tests/test_bia_routes.py`
- **Description:** Add/extend tests asserting: (1) submitting the
  component form with `used_for_authorization` checked and a note
  persists both fields on the `ComponentEnvironment` row and round-trips
  through the edit form; (2) `get_component`/create/update JSON responses
  include the new per-environment keys with correct values; (3) the
  authentication overview export renders the authorisation column
  correctly per component (flagged, unflagged, and no-environment cases)
  and the summary table's flagged-count matches the seeded data.
- **Depends on:** Task 1, Task 2, Task 3, Task 4, Task 5, Task 6
- **Acceptance:** New/updated tests pass and fail if the fields, their
  persistence, serialization, or export rendering regress.
- **Evidence:** `pytest tests/test_bia_routes.py` passes.

## Notes
- No changes to the legacy `Component`-level authentication override field
  or to the `AuthenticationMethod` admin CRUD — confirmed out of scope
  during design (see
  `20260918-1700-authorisation-flag-scope-and-shape.md`).
- No CSV or other export format changes — `export_authentication_overview`
  remains the only rendering surface for this data.
- **Pre-existing test harness issue (unrelated to this feature):** per the
  prior authentication-overview tasks
  (`specs/20260918-055222-description-authentication-overview/tasks.md`),
  `tests/test_bia_routes.py` may fail broadly at fixture setup
  (`DetachedInstanceError` / missing `audit_logs` table) due to a
  pre-existing background-thread/TESTING-flag ordering bug in
  `scaffold/__init__.py`, unrelated to this change. If Task 7's tests hit
  this, verify correctness via a direct `render_template`/form-submission
  script instead, as was done for the prior feature, and note it here.
- **Pre-existing migration multi-head issue:** the migration history
  currently has two heads (`20251205_0015` and `20260830_0001`), found by
  scanning `down_revision` links since `alembic` isn't installed in the
  default environment used for this design conversation. Task 1 must
  resolve this correctly (verify the true current head in an environment
  where `alembic heads` runs, or merge if genuinely diverged) rather than
  guessing.

## Progress
- [x] Task 1: Model & migration - add authorisation fields to ComponentEnvironment
- [x] Task 2: Translations - authorisation field and column labels
- [x] Task 3: Form & sync - capture the flag/note on save
- [x] Task 4: Route - serialize the flag/note and resolve it per component
- [ ] Task 5: Templates - environment editor rows and badge
- [ ] Task 6: Export template - authorisation column and summary count
- [ ] Task 7: Tests - cover persistence, serialization, and export rendering






