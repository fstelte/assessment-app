---
feature: 20261118-074624-risk-workspace-sync-bia-filter
status: planned
created: 2026-11-18
chunk_size: adaptive
total_tasks: 16
estimated_lines: 1380
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

---

# Part 2: Risk Owner Approval Tasks

Implements Part 2 of [design.md](design.md) (decisions 20261118-1038 to
-1058, where 1057 supersedes 1047). Tests are bundled into each task, mostly in a new
`tests/test_risk_approval.py`. The comment max length is 2000 characters,
which resolves the design's open question.

### Foundation

#### Task 10: Approval columns, enum, helpers and migration
- **Estimate:** ~90 lines
- **Files:** `scaffold/apps/risk/models.py`,
  `migrations/versions/20261118_0002_risk_owner_approval.py` (new, follows
  `20261118_0001_risk_residual_mitigated.py`), `scaffold/core/audit.py`,
  `tests/test_risk_approval.py` (new)
- **Description:**
  - `RiskApprovalStatus` enum (`APPROVED`, `REJECTED`), stored with
    `_enum_column(..., name="risk_approval_status")`.
  - Nullable columns `approval_status`, `approval_decided_at` (tz),
    `approval_decided_by_id` (FK users, SET NULL) and `approval_comment`
    (Text), plus the `approval_decided_by` relationship.
  - `approval_state` property: `no_owner` when there's no
    `treatment_owner_id`, otherwise `awaiting`, `approved` or `rejected`.
  - The constant `APPROVAL_MATERIAL_FIELDS = ("chance", "impact",
    "treatment", "residual_chance", "residual_impact",
    "treatment_owner_id")`.
  - `approval_fingerprint()`: a short sha256 of those fields plus
    `is_mitigated`.
  - Add the 4 fields to the `scaffold.apps.risk.models.Risk` entry in the
    audit registry.
  - The migration creates the enum type and columns. The downgrade drops them
    and the type.
- **Depends on:** None
- **Acceptance:** Every state of `approval_state` is covered. The fingerprint
  changes when any material field changes and stays the same for text edits.
- **Evidence:** `pytest tests/test_risk_approval.py` passes. Alembic upgrade
  and downgrade run cleanly on the dev DB.

#### Task 11: Reset listener on material change
- **Estimate:** ~130 lines
- **Files:** `scaffold/apps/risk/models.py`,
  `scaffold/apps/threat/services.py` (`approval_reset` in sync audit
  details), `tests/test_risk_approval.py`
- **Description:**
  - `_reset_risk_approvals(session, flush_context, instances)`, registered
    with `event.listen(db.session, "before_flush", ..., insert=True)` so it
    runs ahead of the audit listener (decision 1057). It's registered once,
    with a guard, and iterates the dirty Risk instances.
  - It compares old and new values through `sa.inspect(risk).attrs`
    history for `APPROVAL_MATERIAL_FIELDS`. For mitigated it compares
    `bool(old mitigated_at)` with `bool(new)`.
  - When any of them changed, it sets the 4 approval columns to None.
  - Tests:
    - Reset: each material field, an owner change, and a mitigated flip both
      ways.
    - No reset: title, description, tickets, components, due date, a new
      `mitigated_at` with the risk still mitigated, and assigning the same
      value.
    - Write paths: the `risk.edit` POST, the admin register edit,
      `apply_payload_to_risk`, `sync_scenario_to_risk` changing the
      likelihood, and `publish_pasta_conclusion_to_risk`.
    - The generic audit row of the update contains the cleared approval
      fields (guards the listener order).
    - The `risk_synced_from_threat` details include `approval_reset`.
    - Closing and reopening a risk keep the approval.
- **Depends on:** Task 10
- **Acceptance:** An approved risk becomes awaiting through every write path
  when a material field changes, and through none of them otherwise.
- **Evidence:** `pytest tests/test_risk_approval.py tests/test_threat_risk_sync.py`
  passes.

### Core Implementation

#### Task 12: Approve and reject routes
- **Estimate:** ~130 lines
- **Files:** `scaffold/apps/risk/forms.py`, `scaffold/apps/risk/routes.py`,
  `scaffold/translations/en.json`, `scaffold/translations/nl.json`,
  `tests/test_risk_approval.py`
- **Description:**
  - `RiskApprovalForm` (FlaskForm): a hidden `fingerprint` and a `comment`
    TextAreaField with `Length(max=2000)`.
  - `POST /risk/<id>/approve` and `/reject`, protected by `@login_required`
    and CSRF.
  - Return 404 for an unknown id, then 403 unless
    `current_user.id == risk.treatment_owner_id`. Admins are not exempt.
  - Any state can be decided, including a flip or a re-approve. Each decision
    overwrites the columns with a new timestamp.
  - Reject without a comment shows a flash error and changes nothing. A
    fingerprint mismatch shows the "risk changed" flash and changes nothing.
  - Sets the status, `decided_at = now(utc)`, `decided_by_id` and the comment
    (stripped, None if empty). Then `log_event("risk_approved" |
    "risk_rejected", "risk", ...)` with the details from decision 1058
    (CHK019). The stale flash text says the comment wasn't saved. Commit, then redirect to `risk.edit`.
- **Depends on:** Task 10
- **Acceptance:** The owner can approve, reject, flip and re-approve, and
  each one creates its own audit event. A non-owner and an admin
  who isn't the owner get 403. A risk with no owner returns 403. The
  stale-page and missing-comment cases change nothing.
- **Evidence:** the route tests in `tests/test_risk_approval.py` pass.

#### Task 13: Approval panel on the edit page
- **Estimate:** ~100 lines
- **Files:** `scaffold/apps/risk/templates/risk/form.html`,
  `scaffold/apps/risk/routes.py` (`edit`), translations,
  `tests/test_risk_approval.py`
- **Description:**
  - `risk.edit` GET passes `approval_form` with the fingerprint pre-filled.
  - Panel at the top, using the Tailwind style already on the page:
    - A state pill, who decided and when, and the comment.
    - When the viewer is the owner: an Approve form (optional comment) and a
      Reject form (required comment), posting to the Task 12 routes.
    - No owner: "Assign an owner to request approval."
    - No current decision but an earlier `risk_rejected` AuditLog: "Previously
      rejected by X on D: comment". A deleted decider shows as "Unknown user".
  - Shown for manual and threat-linked risks alike. Not shown on `risk.new`.
- **Depends on:** Task 12
- **Acceptance:** The owner sees the buttons. A non-owner sees only the state.
  The no-owner message and the earlier rejection reason render when they
  apply.
- **Evidence:** the pytest render tests pass. A browser check is optional,
  not the evidence.

#### Task 14: Dashboard pill and `?approval=` filter [P]
- **Estimate:** ~100 lines
- **Parallel:** Can run with Tasks 12 and 13 (a different function in
  `routes.py`) and with Task 15.
- **Files:** `scaffold/apps/risk/routes.py` (`dashboard`,
  `_build_dashboard_cards`), `scaffold/apps/risk/templates/risk/dashboard.html`,
  translations, `tests/test_risk_approval.py`
- **Description:**
  - `approval=` filters open risks:
    - `mine`: owner = me, and the status is NULL or `rejected`.
    - `awaiting`: there's an owner, and the status is NULL.
    - `rejected`: the status is `rejected`.

    An invalid value is ignored. It combines with `bia`, and the cards, metrics
    and matrix all come from the filtered list.
  - An approval select in the existing filter form, with the "mine" count
    following the BIA filter. Apply and Clear cover both filters. Empty-state
    text.
  - Each card's dict gets `approval_state`. The template shows the pill
    (Awaiting / Approved / Rejected / No owner).
- **Depends on:** Task 10
- **Acceptance:** Each `approval` value lists the right open risks, combines
  with `bia`, and the pills are correct.
- **Evidence:** the dashboard filter tests pass, alone and combined with
  `?bia=`.

#### Task 15: Approval fields in the API [P]
- **Estimate:** ~30 lines
- **Parallel:** Can run with Tasks 12, 13 and 14.
- **Files:** `scaffold/apps/risk/services.py` (`serialize_risk`),
  `scaffold/apps/risk/api.py` (selectinload `approval_decided_by`, if
  needed), `tests/test_risk_api.py`
- **Description:** Additive, read-only fields: `approval_status` (value or
  null), `approval_state`, `approval_decided_at` (ISO),
  `approval_decided_by` (via `_serialize_owner`) and `approval_comment`.
  `apply_payload_to_risk` ignores them.
- **Depends on:** Task 10
- **Acceptance:** GET returns the fields. A PUT that includes them doesn't
  change the approval.
- **Evidence:** `pytest tests/test_risk_api.py` passes.

### Integration & Polish

#### Task 16: Final validation and release notes
- **Estimate:** ~10 lines
- **Files:** none, or small fixes only.
  `specs/20261118-074624-risk-workspace-sync-bia-filter/release-notes.md`
- **Description:**
  - Alembic upgrade and downgrade.
  - Run `pytest tests/test_risk_*.py tests/test_threat_*.py` and the admin
    tests.
  - Check that EN and NL have the same keys.
  - `graphify update .` (not installed here; note it as skipped).
  - Release notes:
    - Every existing risk starts as "awaiting approval".
    - Only the assigned owner can approve. Admins can't.
    - A material change or an owner change resets the approval.
    - The downgrade drops the approval data.
- **Depends on:** Tasks 10–15
- **Acceptance:** Everything passes. No missing translation keys. The release
  notes are updated.
- **Evidence:** test output and migration log.

## Parallel Groups (Part 2)
- Task 10 comes first. Task 11 follows it.
- Tasks 12, 14 and 15 can run together after Task 10. Task 13 follows
  Task 12.
- Task 11 can also run alongside 12, 14 and 15. It only touches the models
  and tests.
- Task 16 comes last.

## Notes (Part 2)
- Task 11: the 7 watched attributes get `active_history=True` (through a
  no-op "set" listener), so an assignment on an expired instance still knows
  the old value and an equal assignment isn't a change. A decision recorded
  in the same flush as a material change is kept, because it's the newer
  event.
- Task 11 tests sign in through the session (as the `login` fixture does).
  17 older risk route, API and action tests still sign in with a password,
  which now forces MFA enrolment, so they fail on HEAD. That's a separate
  cleanup.
- The reset is a session `before_flush` listener with `insert=True`. The
  audit captures diffs in its own `before_flush`, so a mapper `before_update`
  hook would be invisible to it (found by `/minispec.analyze`, decision 1057).
- The listener uses value comparison. With `has_changes()` alone, assigning
  the same enum (the sync does this on every run) would wrongly reset.
- Bulk `query.update()` bypasses the listener. No code path uses it on these
  fields today. Keep it that way.
- The fingerprint includes `treatment_owner_id`. An owner change during an
  open page makes the old owner's decision stale and gets a 403 anyway.
- Deferred: notifications, approving through the API, admin override,
  approval history in the UI.

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
- [x] Task 10: Approval columns, enum, helpers and migration
- [x] Task 11: Reset listener on material change
- [x] Task 12: Approve and reject routes
- [x] Task 13: Approval panel on the edit page
- [x] Task 14: Dashboard pill and ?approval= filter
- [ ] Task 15: Approval fields in the API
- [ ] Task 16: Final validation and release notes
