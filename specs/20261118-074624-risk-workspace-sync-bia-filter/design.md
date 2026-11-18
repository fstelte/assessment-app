---
feature: 20261118-074624-risk-workspace-sync-bia-filter
status: implemented
created: 2026-11-18
decisions:
  - 20261118-0750-risk-sync-components-from-assigned-assets
  - 20261118-0751-risk-mitigated-shows-residual-score
  - 20261118-0800-risk-mitigated-at-and-residual-columns
  - 20261118-0801-risk-workspace-bia-multi-filter
  - 20261118-0802-risk-actual-score-display
  - 20261118-0830-risk-residual-checklist-gap-resolutions
---

# Risk Workspace: Targeted Component Sync, BIA Filter and Actual Risk Score

## Overview

The risk workspace has three problems:

- Threat-synced risks link components the threat model never marked as
  affected. The sync falls back to every component in the BIA.
- The workspace has no BIA filter.
- It shows only the initial score. Mitigated threats are archived instead of
  being shown with their residual exposure.

This feature does the following:

- Links only the components a scenario lists as threatened.
- Adds a server-side, multi-select BIA filter that also scopes the metrics and
  the matrix.
- Stores residual impact, residual chance and `mitigated_at` on every risk,
  synced and manual.
- Shows the **actual** score everywhere: residual when mitigated, initial
  otherwise.

## User Stories

- As a risk owner, I want a synced risk to list only the components the threat
  model marks as threatened, so that the component impact is accurate.
- As a BIA owner, I want to filter the risk workspace to one or more BIAs, so
  that I can review the risks for my services. The counts and the matrix follow
  the filter.
- As a risk reviewer, I want mitigated risks to show their residual score
  (with the initial score as a hint), so that the workspace shows the current
  exposure, not the historical one.
- As a risk manager, I want to mark a manually created risk as mitigated and
  record its residual impact and chance, so that manual and synced risks are
  scored the same way.

## Components

### 1. Component resolution (`threat/services.py::_components_for_scenario`)
- Source: `scenario.assigned_assets`. If that list is empty, fall back to the
  legacy `scenario.asset`.
- Match each asset by name to a `Component` within the threat model's
  `context_scope_id`. The match is case-insensitive and trims whitespace, and
  applies to any `AssetType`. Eligible components are not required. If several
  components share a name, all of them are linked, with duplicates removed by
  id.
- **Remove** the "all components in BIA" fallback. If nothing matches, return
  `[]`.

### 2. Risk model and migration (`risk/models.py`, `migrations/versions/`)
- New nullable columns on `risk_items`: `mitigated_at`, `residual_impact`,
  `residual_chance`.
- Helpers: `is_mitigated`, `residual_score()`, `actual_score()`,
  `actual_chance`, `actual_impact`.

### 3. Threat → risk sync (`threat/services.py::sync_scenario_to_risk`, `risk/routes.py`)
- Close the risk only on `Accepted` or `Closed`. `Mitigated` no longer closes
  it. The existing `treatment == MITIGATE` gate stays: status Mitigated with
  any other treatment still closes the risk.
- **Audit:** log one `risk_synced_from_threat` event per risk, and only when
  something changed. It records the scenario id and before/after values for
  components, mitigated, residual impact and chance, chance, impact, reopened
  and closed. Creating a risk from a scenario logs
  `risk_created_from_threat`.
- When a scenario goes Mitigated → open → Mitigated again, `mitigated_at` gets
  a new timestamp, because it was cleared on reopen.
- Status `Mitigated` sets `mitigated_at`. It keeps an existing timestamp and
  otherwise uses now. Any other open status clears it.
- Copy `residual_likelihood` and `residual_impact` through `_CHANCE_MAP` and
  `_IMPACT_MAP` when they are set. When they are not, clear them.
- The bulk `sync_from_threats` no longer skips `Mitigated` scenarios.
- The `risk.edit` GET calls `sync_scenario_to_risk(linked_scenario)` instead
  of its own inline re-sync. This gives one code path and one audit rule.
- A newly created risk with no components follows the same rules.

### 4. Risk form (`risk/forms.py`, `risk/templates/risk/form.html`, `risk/routes.py`)
- Add a "Mitigated" checkbox and residual impact and chance selects (optional).
- On save: checked with no timestamp → set it to now. Unchecked → clear it.
- **Threat-linked risks:** every field the sync owns is shown **read-only**:
  title, description, chance, impact, treatment, residual impact and chance,
  Mitigated, components and controls. A "Managed by threat scenario" note
  links to the scenario (amendment to decision 0830). Posted values for those
  fields are ignored. The component requirement and the "Mitigate needs a
  control" requirement are skipped. Impact areas, treatment plan, owner, due
  date, tickets and discovered on stay editable. Manual risks still need at
  least one component.
- Manual risks may store residual values while Mitigated is unchecked. Those
  values don't affect the score.
- PASTA-published risks are not scenario-linked, so they stay fully editable.
  Republishing does not touch `mitigated_at` or the residual values.
- A residual score higher than the initial score is allowed. There is no
  validation for it.
- The score panel shows the actual score, and the initial score as a hint when
  the risk is mitigated.
- `log_event` details include `mitigated` and the residual values.

### 5. Dashboard display (`risk/routes.py`, `risk/templates/risk/dashboard.html`)
- Cards: the main number and severity use the actual score. Mitigated risks get
  a "Mitigated" pill and an "Initial: X → Residual: Y" line. Mitigated with no
  residual values shows "Mitigated – residual not set".
- Matrix: each risk is placed at `(actual_chance, actual_impact)` and shows the
  actual score.
- Metrics: "high" counts by actual severity. The "mitigate" metric is
  relabelled "Treatment: mitigate".
- A risk that is both closed and mitigated shows both pills and the actual
  score. Closed risks stay in the matrix, as today.
- The matrix heading and footnote say the matrix shows the actual score
  (residual when mitigated).

### 6. BIA filter (`risk/routes.py::dashboard`, `dashboard.html`)
- `GET /risk/?bia=<id>&bia=<id>`. With no param, all risks are shown.
- Filter: `Risk.components.any(Component.context_scope_id.in_(ids))`.
- Options: BIAs that have at least one component, sorted by name. Selected
  values stay selected after the page reloads. There is a Clear link.
- Cards, metrics and the matrix all come from the filtered list. Under a
  filter, "Components impacted" counts only components in the selected BIAs.
- Archived risks are still shown when a filter is active. Risks without
  components (for example, threat models with no BIA) match no filter.
- Access is unchanged: any authenticated user sees every BIA option, since BIA
  names already appear on the cards.

### 8. Other score surfaces (`admin/routes.py`, `ssp/routes.py`)
- The admin risk register list and edit page use `actual_score()` and the
  matching severity.
- The SSP risk severity summary uses actual severity. This prevents an
  over-count, because mitigated risks no longer close.

### 7. API (`risk/services.py::serialize_risk`)
- Additive fields: `mitigated_at`, `residual_impact`, `residual_chance`,
  `residual_score`, `actual_score`, `actual_severity`.
- `score` and `severity` keep their current meaning (initial).
- `apply_payload_to_risk` accepts `residual_impact`, `residual_chance` and
  `mitigated` (bool), all optional. An omitted field is left unchanged. An
  explicit `null` clears a residual field. `mitigated: true` keeps an existing
  `mitigated_at`.

## Data Model

```
risk_items
  + mitigated_at      TIMESTAMPTZ NULL
  + residual_impact   VARCHAR (risk_impact values) NULL
  + residual_chance   VARCHAR (risk_chance values) NULL
```

Existing rows: all three are NULL, so the actual score equals the initial
score. Nothing changes until they are re-synced or edited. Risks that the old
sync archived because their scenario was mitigated come back on the next sync.
The sync clears `closed_at` for open statuses, as it already does today.

## API/Interface

- `GET /risk/?bia=<int>[&bia=<int>...]` – filtered dashboard.
- `POST /risk/sync-from-threats` – now includes mitigated scenarios.
- Risk form: new fields `mitigated` (bool), `residual_impact`,
  `residual_chance`.
- `serialize_risk()` – the additive fields listed above.
- `Risk.actual_score() -> int`, `Risk.residual_score() -> int | None`,
  `Risk.is_mitigated -> bool`, `Risk.actual_chance`, `Risk.actual_impact`.

## Out of Scope

- PASTA conclusions (`publish_pasta_conclusion_to_risk`): no residual concept,
  so they are unchanged.
- Changing how assets map to components (still by name). There is no FK link.
- Client-side filtering, saved filters, and filters other than BIA.
- Exports: the risk module has no CSV or PDF exports, so there is nothing to
  change.

## Rollout

The release notes (PR and GitHub release) must state three things:
- Synced risks lose the components they got from the old "all components"
  fallback.
- Archived risks of mitigated scenarios reopen on the next sync.
- The migration's downgrade drops the residual and mitigated data.

## Validation

- pytest: `_components_for_scenario` uses only assigned assets and returns
  `[]` when nothing matches.
- pytest: mitigated scenarios keep the risk open and copy the residual values.
  Accepted and Closed still close it.
- pytest: `actual_score()` covers mitigated with and without residual values,
  and not mitigated.
- pytest: the dashboard BIA filter (single, multiple, invalid ids), and the
  metrics and matrix following the filter.
- pytest: the manual form's mitigated checkbox and residual values, and the
  empty-components rule for threat-linked risks.
- Migration upgrade and downgrade on the dev DB.
- Translations: new keys in `en.json` and `nl.json`.

## Open Questions

None. Both earlier questions are settled in
`20261118-0830-risk-residual-checklist-gap-resolutions`:
- Synced fields are read-only for linked risks.
- Archived risks are shown when a filter is active.
