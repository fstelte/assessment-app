---
feature: 20260918-055222-description-authentication-overview
status: planned
created: 2026-09-18
chunk_size: medium
total_tasks: 5
estimated_lines: 230
---

# Authentication Overview Export: Info type & Tier Tasks

## Overview

Implements the design in `design.md`: adds Info type and Tier columns to
the Authentication Overview export's detail tables, and a new nested
Tier -> Info type summary table, per the linked decision records.

**Note on Tier locale behavior:** `BiaTier.get_label()` takes no
meaningful locale argument — internally it resolves the tier name via the
current request/session locale, unlike
`AuthenticationMethod.label_for_locale(locale)` which forces a specific
locale. Tier text therefore renders in a single, current-locale-dependent
language, not bilingually like the Method summary elsewhere in this
export. Tasks 1, 2, and 5 below reflect this: call `get_label()` with no
argument, and tests should assert against the app's actual default/request
locale rather than trying to force a locale via an argument.

## Task List

### Foundation

#### Task 1: Route - eager-load Tier and build the nested summary structure
- **Estimate:** ~65 lines
- **Files:** `scaffold/apps/bia/routes.py`
- **Description:** Add `joinedload(Component.context_scope).joinedload(ContextScope.tier)`
  to the existing query in `export_authentication_overview` to avoid N+1
  queries now that Tier is rendered per row. Add a helper (e.g.
  `_build_tier_summary(components)`) that groups components by
  `tier.level` (ascending, `None`/no-tier group last) and then, within each
  tier, by `info_type` normalized as `(value or "").strip().lower()` for
  the grouping key (blank/whitespace-only/`None` all map to a final "Not
  set" group), displayed using one occurrence of the original casing,
  alphabetical ascending with "Not set" last. Produces a count per
  (tier, normalized info_type) combination; renders as an empty structure
  (no special-casing) when there are zero components. Pass the result to
  the template as `tier_summary`.
- **Depends on:** None
- **Acceptance:** `export_authentication_overview` returns a `tier_summary`
  structure with correct grouping/ordering/counts for a mix of
  tiered/untiered, info_type-set/unset/whitespace/mixed-case-duplicate
  components, and an empty structure when there are no components.
- **Evidence:** `pytest tests/test_bia_routes.py` passes (grouping
  correctness for `_build_tier_summary` is exercised by Task 5's tests,
  not a separate unit test file, since this codebase tests BIA routes
  through integration-style Flask test-client tests).

#### Task 2: [P] Template - add Info type & Tier columns to detail tables
- **Estimate:** ~30 lines
- **Parallel:** Can run with Task 3
- **Files:** `scaffold/apps/bia/templates/bia/export_authentication.html`
- **Description:** Add two `<th>`/`<td>` pairs, in column order
  `BIA, Component, Tier, Info type, Owner, Users`, to the per-method group
  table and the unassigned table: `component.context_scope.tier.get_label()`
  (no locale argument — see the locale note above) and `component.info_type`
  (raw value, not normalized), both falling back to the existing `not_set`
  translation string when blank/whitespace-only or `None`/no tier. No
  truncation — long values wrap using default table-cell behavior like the
  existing Owner/Users columns.
- **Depends on:** None
- **Acceptance:** Rendered export HTML shows Tier and Info type values (or
  "Not set") in the correct column position for every component row in
  both table types.
- **Evidence:** `pytest tests/test_bia_routes.py` passes; manual render
  check of the export HTML.

#### Task 3: [P] Translations - new column and summary keys
- **Estimate:** ~30 lines (across 2 files)
- **Parallel:** Can run with Task 2
- **Files:** `scaffold/translations/en.json`, `scaffold/translations/nl.json`
- **Description:** Add `columns.info_type` and `columns.tier` under
  `bia.export.authentication_overview`, plus a new `tier_summary`
  namespace (title, tier/info-type/components column headers, tier and
  info-type "not set" labels) in both locale files, following the existing
  key structure and naming conventions.
- **Depends on:** None
- **Acceptance:** New keys resolve correctly in both `en` and `nl` locales
  with no missing-translation fallback warnings.
- **Evidence:** App starts without translation errors; keys render as
  expected text in both locales.

### Core Implementation

#### Task 4: Template - new nested Tier/Info type summary table
- **Estimate:** ~50 lines
- **Files:** `scaffold/apps/bia/templates/bia/export_authentication.html`
- **Description:** Render `tier_summary` (from Task 1) as a new table
  placed alongside the existing method-summary table at the top of the
  export: Tier group header rows (using the new `tier_summary` translation
  keys from Task 3), Info type sub-rows within each tier, and a component
  count per row. When `tier_summary` is empty, render the table with an
  empty body and no dedicated empty-state message.
- **Depends on:** Task 1, Task 3
- **Acceptance:** Export shows a correctly grouped/ordered/counted
  Tier -> Info type summary table matching the design's nested-counts
  structure, including the zero-component case.
- **Evidence:** Manual render check against seeded data with multiple
  tiers/info types, including untiered/unset and zero-component cases.

### Integration & Polish

#### Task 5: Tests - cover new columns and summary table
- **Estimate:** ~65 lines
- **Files:** `tests/test_bia_routes.py`
- **Description:** Extend or add tests asserting: Tier/Info type values
  render in the correct column position in detail rows for both table
  types, "Not set" placeholders appear when blank/whitespace-only/None,
  and the new summary table shows correct per-(tier, info_type) counts in
  the expected order (tier ascending with untiered last, info_type
  alphabetical with unset last), including a case verifying that
  mixed-case/whitespace-variant info_type values (e.g. "Customer Data" vs
  " customer data ") merge into one summary group while still displaying
  their raw values in the detail columns. Assert Tier text against the
  app's actual default/request locale (do not attempt to force a locale by
  passing an argument to `get_label`, since it has no effect).
- **Depends on:** Task 1, Task 2, Task 3, Task 4
- **Acceptance:** New/updated tests pass and fail if the columns, column
  order, summary table, or normalization behavior regress.
- **Evidence:** `pytest tests/test_bia_routes.py` passes.

## Notes
- No schema changes or Alembic migration needed; reuses existing
  `Component.info_type` and `ContextScope.tier` -> `BiaTier` fields.
- Tasks 2 and 3 have no shared dependency and can be worked in either
  order or together.
- No audit-log, access-control, documentation, or other-export-format
  changes are in scope (confirmed during checklist review — see
  20260918-0552-authentication-overview-gap-resolutions.md).
- `BiaTier.get_label()`'s `locale` argument is inert (see locale note
  above) — flagged during `/minispec.analyze` on 2026-09-18.
- **Pre-existing test harness issue (unrelated to this feature) -- ROOT CAUSE FOUND:**
  `tests/test_bia_routes.py` fails broadly with `DetachedInstanceError` on
  the `active_user`/`login` fixtures and `no such table: audit_logs` /
  `SystemError` from a background thread. Root cause: `scaffold/__init__.py`
  line ~619 guards the audit-prune background thread with
  `if app.testing: return`, but `tests/conftest.py`'s `app` fixture calls
  `app.config.update(TESTING=True, ...)` *after* `create_app(settings)`
  already returned, and `_schedule_background_tasks` (which starts that
  thread) runs inside `create_app()`. So the guard checks `app.testing`
  before it is ever set, the thread starts in every test run, and it hits
  the in-memory SQLite DB from a separate thread/connection, corrupting or
  missing the schema. This is a pre-existing bug unrelated to this
  feature -- confirmed via `git stash` that it reproduces identically on
  unmodified `main`. Recommended fix (out of scope here): pass
  `testing=True` through `Settings`/`create_app` itself, or otherwise set
  `TESTING` before `_schedule_background_tasks` runs, rather than after
  `create_app()` returns.
- Task 5's tests (added) fail at fixture *setup* (the `login` fixture)
  due to the above, before the test body ever runs. Their correctness was
  instead verified via a direct `render_template`/`_build_tier_summary`
  script (same approach used to verify Task 4), using equivalent seed
  data. They are expected to pass once the harness bug above is fixed.

## Progress
- [x] Task 1: Route - eager-load Tier and build the nested summary structure
- [x] Task 2: Template - add Info type & Tier columns to detail tables
- [x] Task 3: Translations - new column and summary keys
- [x] Task 4: Template - new nested Tier/Info type summary table
- [x] Task 5: Tests - cover new columns and summary table (blocked from
      running by the pre-existing harness bug above; logic verified via
      direct render instead of pytest)





