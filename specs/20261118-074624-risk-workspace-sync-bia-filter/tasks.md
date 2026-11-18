---
feature: 20261118-074624-risk-workspace-sync-bia-filter
status: implemented
created: 2026-11-18
chunk_size: adaptive
total_tasks: 9
estimated_lines: 780
---

# Risk Workspace: Targeted Component Sync, BIA Filter and Actual Risk Score Tasks

## Overview

Implements [design.md](design.md):
- Threat → risk sync links only the threatened components.
- Risks get `mitigated_at` and residual impact and chance, for synced and
  manual risks.
- The workspace shows the actual score (residual when mitigated) on cards, the
  matrix, metrics and the API.
- The dashboard gets a server-side, multi-select BIA filter.

Tests are bundled into each task. No sync tests exist yet, so Task 1 creates
`tests/test_threat_risk_sync.py`.

## Task List

### Foundation

#### Task 1: Component resolution uses threatened assets only
- **Estimate:** ~60 lines
- **Parallel:** Can run with Task 2
- **Files:** `scaffold/apps/threat/services.py`, `tests/test_threat_risk_sync.py` (new)
- **Description:** Rewrite `_components_for_scenario`:
  - Collect asset names from `scenario.assigned_assets`. If that list is
    empty, use `scenario.asset`.
  - Match them to `Component`s by name within the threat model's
    `context_scope_id`. The match is case-insensitive and trims whitespace,
    and applies to any asset type. Eligibility is not required.
  - Return `[]` when there is no scope or no match. Remove the "all components
    in BIA" fallback.
  - Remove duplicates.
- **Depends on:** None
- **Acceptance:**
  - A scenario with 2 of 4 BIA components threatened gets exactly those 2.
  - Legacy `asset` only → its match.
  - No assets, or no match → `[]`.
  - No context scope → `[]`.
  - A component in another BIA with the same name is not linked.
  - Names that differ only in case or surrounding whitespace match.
  - Two components with the same name in one BIA are both linked.
- **Evidence:** `pytest tests/test_threat_risk_sync.py` passes.

#### Task 2: Risk residual columns, helpers and migration
- **Estimate:** ~90 lines
- **Parallel:** Can run with Task 1
- **Files:** `scaffold/apps/risk/models.py`, `migrations/versions/20261118_0001_risk_residual_mitigated.py` (new, `down_revision = "20261107_0001"`), `tests/test_risk_models_residual.py` (new)
- **Description:**
  - Add nullable `mitigated_at` (tz DateTime), `residual_impact` (`risk_impact`
    enum) and `residual_chance` (`risk_chance` enum).
  - Add `is_mitigated`, `residual_score()`, `actual_score()`, `actual_chance`,
    `actual_impact` and `determine_actual_severity(thresholds)`.
  - The migration adds and drops the columns. Use non-native enum strings,
    matching how the existing columns are stored.
- **Depends on:** None
- **Acceptance:**
  - Not mitigated → actual equals initial.
  - Mitigated with both residual values → actual equals residual.
  - Mitigated with a residual value missing → actual equals initial, and
    `residual_score()` is `None`.
- **Evidence:** the new model tests pass. `flask db upgrade` then
  `flask db downgrade` runs cleanly on the dev DB.

### Core Implementation

#### Task 3: Sync carries the mitigated state and residual values, with audit
- **Estimate:** ~120 lines
- **Files:** `scaffold/apps/threat/services.py`, `scaffold/apps/risk/routes.py` (`sync_from_threats`), `tests/test_threat_risk_sync.py`
- **Description:** In `sync_scenario_to_risk`:
  - Close the risk only for `Accepted` and `Closed` (and for non-MITIGATE
    treatment, as today).
  - Status `Mitigated` sets `mitigated_at`, keeping an existing value. Other
    open statuses clear it.
  - Map `residual_likelihood` and `residual_impact` through
    `_CHANCE_MAP`/`_IMPACT_MAP`, or set them to `None` when unset.
  - Drop `MITIGATED` from the exclusion set in the bulk `sync_from_threats`.
  - The treatment gate stays: Mitigated with a treatment other than Mitigate
    still closes the risk.
  - **Audit:** snapshot the synced fields before and after. If anything
    changed, call `log_event(action="risk_synced_from_threat",
    entity_type="risk", ...)` with the scenario id and the before/after values
    of the changed fields only:
    - components (ids)
    - mitigated
    - residual impact and chance
    - chance and impact
    - reopened and closed

    A new risk logs `risk_created_from_threat`.
- **Depends on:** Task 1, Task 2
- **Acceptance:**
  - A Mitigated scenario keeps its risk open and sets `mitigated_at` and the
    residual values.
  - Re-syncing keeps the original `mitigated_at`.
  - Back to Analysed → `mitigated_at` is cleared.
  - Accepted and Closed → the risk is closed.
  - A previously archived risk of a mitigated scenario is reopened.
  - The bulk sync counts mitigated scenarios.
  - Mitigated → Analysed → Mitigated gives a new `mitigated_at`.
  - Mitigated with treatment Accept closes the risk.
  - A no-op re-sync writes no audit event. A change writes exactly one, with
    only the changed fields.
- **Evidence:** `pytest tests/test_threat_risk_sync.py` passes.

#### Task 4: Risk edit form: re-sync, mitigated/residual fields, read-only synced fields for linked risks
- **Estimate:** ~170 lines
- **Parallel:** Can run with Tasks 5 and 6
- **Files:** `scaffold/apps/risk/routes.py` (`edit`, `create`), `scaffold/apps/risk/forms.py`, `scaffold/apps/risk/services.py` (`configure_risk_form`, choices), `scaffold/apps/risk/templates/risk/form.html`, `scaffold/translations/en.json`, `scaffold/translations/nl.json`, `tests/test_risk_routes.py`
- **Description:**
  - **Edit GET re-sync:** replace the inline re-sync block with
    `sync_scenario_to_risk(linked_scenario)` and commit. This gives a single
    code path, with auditing from Task 3.
  - **Form:** add a `mitigated` BooleanField and `residual_impact` and
    `residual_chance` selects, each with a blank option.
  - **Saving (create and edit):** checked with no timestamp → set it to now.
    Unchecked → clear it. Blank residual → `None`.
  - **Threat-linked risks:** render every sync-owned field disabled (title,
    description, chance, impact, treatment, residual impact and chance,
    Mitigated, components, controls), with a "Managed by threat scenario"
    note that links to the scenario (amendment to decision 0830).
  - On POST, ignore those fields: don't validate components, don't overwrite
    them. Manual and PASTA risks stay fully editable, and manual risks still
    need at least one component.
  - Manual risks may store residual values while Mitigated is unchecked.
  - **Audit:** `log_event` details include `mitigated`, `residual_impact` and
    `residual_chance`.
  - **Score panel:** show the actual score, with "Initial → Residual" when
    mitigated.
  - **Translations:** add all new keys in EN and NL.
- **Depends on:** Task 3
- **Acceptance:**
  - A manual risk can be marked mitigated with residual values, and the edit
    page shows the residual as the actual score.
  - Unchecking clears `mitigated_at`.
  - A linked risk with no matching components saves without a component error.
  - Posting a different chance or Mitigated value for a linked risk leaves the
    stored values unchanged.
  - The linked-risk form renders those fields disabled, with the note.
  - A manual risk with no components is still rejected.
- **Evidence:** `pytest tests/test_risk_routes.py` passes, with new cases.

#### Task 5: Dashboard shows the actual score
- **Estimate:** ~100 lines
- **Parallel:** Can run with Tasks 4 and 6
- **Files:** `scaffold/apps/risk/routes.py` (`_build_dashboard_cards`, `_dashboard_metrics`, `_build_risk_matrix`), `scaffold/apps/risk/templates/risk/dashboard.html`, `scaffold/translations/en.json`, `scaffold/translations/nl.json`, `tests/test_risk_routes.py`
- **Description:**
  - **Cards:** add `actual_score` and `actual_severity` (used for the main
    number and pill), plus `initial_score`, `residual_score` and
    `is_mitigated`.
  - **Template:** a "Mitigated" pill and an "Initial: X → Residual: Y" line.
    Show "Mitigated – residual not set" when the residual is missing.
  - **Matrix:** place each risk at `(actual_chance, actual_impact)` and use the
    actual score.
  - **Metrics:** the "high" count uses actual severity. Relabel the
    "mitigate" metric "Treatment: mitigate".
  - **Matrix copy:** the heading and footnote say "actual score (residual when
    mitigated)".
  - **Closed and mitigated risks:** show both pills and the actual score.
- **Depends on:** Task 2
- **Acceptance:**
  - A mitigated risk with initial 4×4 and residual 2×3 shows 6 on its card,
    sits in the possible×minor cell, and is not counted as high (with the
    default thresholds).
  - An unmitigated risk is unchanged.
- **Evidence:** `pytest tests/test_risk_routes.py` passes. Manual check of
  `/risk/` in the browser.

#### Task 6: API exposes residual and actual fields
- **Estimate:** ~70 lines
- **Parallel:** Can run with Tasks 4 and 5
- **Files:** `scaffold/apps/risk/services.py` (`serialize_risk`, `apply_payload_to_risk`), `tests/test_risk_api.py`
- **Description:**
  - `serialize_risk` adds `mitigated_at` (ISO), `residual_impact`,
    `residual_chance`, `residual_score`, `actual_score` and `actual_severity`.
    `score` and `severity` stay unchanged.
  - `apply_payload_to_risk` accepts optional `residual_impact`,
    `residual_chance` (through `_coerce_weighted_enum`, allowing null) and
    `mitigated` (bool → set or clear `mitigated_at`; `true` keeps an existing
    timestamp).
  - An omitted field is left unchanged. An explicit `null` clears a residual
    field.
- **Depends on:** Task 2
- **Acceptance:**
  - GET returns the new fields.
  - PATCH/POST with residual values and `mitigated: true` stores them.
  - An invalid residual value returns a field error.
  - Existing API tests still pass.
- **Evidence:** `pytest tests/test_risk_api.py` passes.

### Integration & Polish

#### Task 7: BIA multi-filter on the risk dashboard
- **Estimate:** ~90 lines
- **Files:** `scaffold/apps/risk/routes.py` (`dashboard`), `scaffold/apps/risk/templates/risk/dashboard.html`, `scaffold/translations/en.json`, `scaffold/translations/nl.json`, `tests/test_risk_routes.py`
- **Description:**
  - Parse `request.args.getlist("bia")` as ints and drop invalid values.
  - When ids are given, filter with
    `Risk.components.any(Component.context_scope_id.in_(ids))`.
  - The BIA options are the `ContextScope`s that have at least one component,
    sorted by name.
  - The filter form is a Tailwind multi-select with Apply and Clear. It keeps
    the current selection.
  - Cards, metrics and the matrix all use the filtered list. Under a filter,
    "Components impacted" counts only components in the selected BIAs.
  - Archived risks are still shown.
- **Depends on:** Task 5 (same route and template)
- **Acceptance:**
  - `?bia=A` shows only risks with a component in A.
  - `?bia=A&bia=B` shows the union.
  - `?bia=x` and unknown ids are ignored, and all risks show.
  - With the filter on, the total metric and matrix counts match the number of
    visible cards.
  - Risks with no components are hidden only when a filter is active.
- **Evidence:** `pytest tests/test_risk_routes.py` passes. Manual browser
  check.

#### Task 8: Admin risk register and SSP summary use the actual score [P]
- **Estimate:** ~40 lines
- **Parallel:** Can run with Tasks 4–7
- **Files:** `scaffold/apps/admin/routes.py` (risk list around line 1213, edit around line 1306), `scaffold/apps/admin/templates/admin/` (risk list and edit, if they label the score), `scaffold/apps/ssp/routes.py` (around line 225), tests for both
- **Description:**
  - The admin list and edit pages use `risk.actual_score()` and the matching
    severity.
  - The SSP risk severity summary uses actual severity.
  - Keep the existing template attribute names. Adjust labels only where they
    say "inherent".
- **Depends on:** Task 2
- **Acceptance:**
  - A mitigated risk with initial 16 and residual 6 shows 6 in the admin list.
  - The SSP summary counts it under the residual severity, not the initial
    one.
  - Closed risks are still excluded from the SSP summary.
- **Evidence:** the targeted admin and SSP tests pass.

#### Task 9: Final validation and release notes
- **Estimate:** ~10 lines
- **Files:** none, or small fixes only
- **Description:**
  - Run migration upgrade and downgrade.
  - Run `pytest tests/test_risk_*.py tests/test_threat_*.py` and the admin and
    SSP tests.
  - Check that EN and NL have the same keys.
  - Run `graphify update .` (it is not installed here; note that it was
    skipped).
  - Draft release notes in the PR description:
    - Synced risks lose their fallback components.
    - Archived risks of mitigated scenarios reopen.
    - The downgrade drops the residual data.
- **Depends on:** Tasks 1–8
- **Acceptance:** Everything passes. No missing translation keys. The release
  notes are present.
- **Evidence:** test output and migration log recorded in the PR description.

## Parallel Groups
- Tasks 1 and 2 can run together.
- Tasks 4, 5 and 6 can run together once Tasks 2 and 3 are done. Tasks 4 and 5
  both touch `risk/routes.py` and the translations, but in different
  functions.
- Task 7 runs after Task 5.
- Task 8 can run any time after Task 2.

## Notes
- Linked risks: the scenario owns chance, impact, residual values,
  `mitigated_at` and components. The form shows these fields read-only and
  ignores posted values for them (decision 0830).
- Existing synced risks lose their fallback components on the next sync, and
  archived risks of mitigated scenarios reopen. Mention both in the release
  notes.
- `publish_pasta_conclusion_to_risk` is out of scope.
- Follow-up: the risk API (PUT) can still change sync-owned fields of
  threat-linked risks, which the next sync overwrites. Not in scope here.
- Fixed while doing Task 6: an API PUT that kept an existing impact area
  violated `uq_risk_impact_area` (a 500 error).
- Task 8 also covered the SSP PDF export (`ssp/routes.py::export_pdf`), which
  builds the same risk summary as the SSP view.
- Follow-up: the SSP risk summary counts a risk once per linked component in
  the BIA, so it can count the same risk twice. This was already the case.
- Run `graphify update .` after code changes (CLAUDE.md). The `graphify` CLI is
  not installed in this environment.

## Progress
- [x] Task 1: Component resolution uses threatened assets only
- [x] Task 2: Risk residual columns, helpers and migration
- [x] Task 3: Sync carries the mitigated state and residual values, with audit
- [x] Task 4: Risk edit form: re-sync, mitigated/residual fields, read-only synced fields for linked risks
- [x] Task 5: Dashboard shows the actual score
- [x] Task 6: API exposes residual and actual fields
- [x] Task 7: BIA multi-filter on the risk dashboard
- [x] Task 8: Admin risk register and SSP summary use the actual score
- [x] Task 9: Final validation and release notes
