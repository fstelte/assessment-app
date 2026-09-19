---
feature: authentication-overview-environments
status: planned
created: 2026-09-19
chunk_size: adaptive
total_tasks: 3
estimated_lines: 140
---

# Authentication Overview Export: Environments column Tasks

## Overview

Implements [design.md](design.md): remove the tier/info type summary and the
Users column from the Authentication Overview export, and add an
Environments column (enabled environments + their authentication method).

## Task List

### Foundation

#### Task 1: Route - drop tier summary, build environment usage
- **Estimate:** ~40 lines
- **Files:** `scaffold/apps/bia/routes.py`, `tests/test_bia_routes.py`
- **Description:** Delete `_build_tier_summary()` and the `tier_summary=` render argument, and delete `test_export_authentication_overview_tier_summary_merges_and_orders` in `tests/test_bia_routes.py` (it would otherwise fail until Task 2 removes the template section). In `export_authentication_overview`, build `environment_usage = {component.id: [(env_label, method_label_or_None), ...]}` from the already-loaded `component.environments` (enabled only, `ENVIRONMENT_TYPES` order) using the route helpers `_environment_label` and `_describe_environment_authentication`, and pass it to the template.
- **Depends on:** None
- **Acceptance:** Route renders without `tier_summary`; `environment_usage` contains an entry for every exported component.
- **Evidence:** `pytest tests/test_bia_routes.py -k authentication_overview` passes with the summary test removed.

### Core Implementation

#### Task 2: Template and translations
- **Estimate:** ~50 lines
- **Files:** `scaffold/apps/bia/templates/bia/export_authentication.html`, `scaffold/translations/en.json`, `scaffold/translations/nl.json`
- **Description:** Remove the "Components by tier and info type" section; remove the Users `<th>`/`<td>` in the method tables and the unassigned table; add an Environments column in the same position (one `env: method` line per entry, "Not set" for missing method or no enabled environments). Remove the `tier_summary` and `columns.users` keys; add `columns.environments` ("Environments" / "Omgevingen").
- **Depends on:** Task 1
- **Acceptance:** Export shows Environments and no "User types"/"Components by tier and info type"; both JSON files remain valid and in sync.
- **Evidence:** Both translation files parse as JSON, no `user_type`/`tier_summary` reference remains in the template (`Select-String`), and a manual render of the export shows the Environments column. (Automated environment assertions land in Task 3.)

### Integration & Polish

#### Task 3: Tests
- **Estimate:** ~50 lines
- **Files:** `tests/test_bia_routes.py`
- **Description:** Add a test with a component enabled in production (IdP) and test (Application integrated) plus a disabled development environment, asserting both enabled lines appear, the disabled one does not, and "User types" / "Components by tier and info type" are absent. Add a case for a component with no enabled environments showing "Not set". Add a case for a component grouped by the legacy `Component.authentication_method_id` with no enabled environments, asserting the Environments cell shows Not set while the component stays under its method. Confirm the existing tier/info type and authorisation export tests still pass, and, if Playwright is installed, render the PDF variant (`format=pdf`) once as a manual, non-blocking check that the extra column does not break the layout (skip with a note otherwise).
- **Depends on:** Task 2
- **Acceptance:** New and existing export tests pass.
- **Evidence:** `pytest tests/test_bia_routes.py` passes.

## Notes
- No schema change and no migration.
- `Component.user_type` stays in the model, forms, and other views.
- Known edge case: a legacy-override component with no enabled environments shows Not set in Environments (see decision record).
- Deferred: flagging the authorisation environment inside the Environments cell.
- The Write and Edit tools fail in this session (temp-file ENOENT); edit files via PowerShell.
- The test suite cannot log in here: the `active_user` fixture in `tests/conftest.py` raises `DetachedInstanceError`, and even with that worked around, authenticated requests return 302. This fails identically on the untouched code, so pytest evidence is unavailable until the fixture/environment is fixed.

## Progress
- [x] Task 1: Route - drop tier summary, build environment usage (commit cf4c161; pytest evidence blocked by the existing test-login issue, verified by compile check and a direct run of the new comprehension)
- [ ] Task 2: Template and translations
- [ ] Task 3: Tests
