---
feature: 20261118-074624-risk-workspace-sync-bia-filter
status: planned
created: 2026-11-18
decisions:
  - 20261118-0750-risk-sync-components-from-assigned-assets
  - 20261118-0751-risk-mitigated-shows-residual-score
  - 20261118-0800-risk-mitigated-at-and-residual-columns
  - 20261118-0801-risk-workspace-bia-multi-filter
  - 20261118-0802-risk-actual-score-display
  - 20261118-0830-risk-residual-checklist-gap-resolutions
  - 20261118-1038-risk-approval-by-treatment-owner
  - 20261118-1039-risk-approval-scope-and-reset
  - 20261118-1045-risk-approval-columns-and-states
  - 20261118-1046-risk-approval-owner-only
  - 20261118-1047-risk-approval-reset-listener
  - 20261118-1048-risk-approval-dashboard-entry
  - 20261118-1057-risk-approval-reset-before-flush
  - 20261118-1058-risk-approval-checklist-gap-resolutions
  - 20261118-1200-risk-workspace-hides-closed-risks
  - 20261118-1201-risk-overview-table
  - 20261118-1202-risk-cards-collapsible
  - 20261118-1203-risk-reopen-from-edit-page
  - 20261118-1210-risk-workspace-overview-checklist-resolutions
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

---

# Part 2: Risk Owner Approval

> Added 2026-11-18 on the same branch. Part 1 above is implemented. Part 2 is
> designed but not yet built.

## Overview

The risk's owner (`treatment_owner`) approves or rejects the risk's
assessment. That covers chance, impact and treatment, plus the residual score
and mitigated state when they are set. The approval stays valid until one of
those material fields changes or the owner is reassigned. When that happens,
the risk goes back to "awaiting approval", whichever path made the change:
form, admin, API, threat sync or PASTA. Owners find their pending risks through
an "Awaiting my approval" filter on the risk dashboard.

## User Stories

- As a risk owner, I want to see the risks waiting for my approval, so that I
  can work through them.
- As a risk owner, I want to approve a risk's score and treatment, so that
  there's a record that I accept it.
- As a risk owner, I want to reject a risk with a comment, so that the risk
  manager knows what to revise.
- As a risk manager, I want to see each risk's approval state on the
  dashboard, so that I know which risks still need sign-off.
- As an auditor, I want approvals, rejections and resets in the audit trail,
  so that sign-off is traceable.

## Components

### 9. Approval model and migration (`risk/models.py`, `migrations/versions/`)
- `RiskApprovalStatus` enum: `APPROVED`, `REJECTED`. NULL means awaiting
  approval.
- New nullable columns: `approval_status`, `approval_decided_at`,
  `approval_decided_by_id` (FK users, SET NULL) and `approval_comment`.
- Relationship `approval_decided_by`. Helper `approval_state` returns
  `"no_owner" | "awaiting" | "approved" | "rejected"`.
- Helper `approval_fingerprint()` returns a short hash of the material fields,
  used by the stale-view guard.
- Existing rows are left NULL, so every risk starts as awaiting approval.

### 10. Reset listener (`risk/models.py`)
- A session `before_flush` listener, registered with `insert=True` so that it
  runs ahead of the generic audit (decision 1057, which supersedes 1047). For
  each dirty Risk: if `chance`, `impact`, `treatment`,
  `residual_chance`, `residual_impact` or `treatment_owner_id` changed value,
  or whether the risk is mitigated flipped, it clears the four approval
  columns.
- A new `mitigated_at` timestamp alone, with the risk mitigated before and
  after, does **not** reset.
- Add the four approval fields to the Risk entry in `core/audit.py`'s model
  registry, so resets and decisions are audited automatically.
- The material fields are one constant, `APPROVAL_MATERIAL_FIELDS`, which the
  fingerprint shares.
- `risk_synced_from_threat` details gain `approval_reset: bool`.
- Closing or reopening a risk doesn't reset the approval. A user deletion that
  sets the owner to NULL at the DB level shows as "No owner". Assigning a new
  owner resets the decision.

### 11. Approve and reject routes (`risk/routes.py`)
- `POST /risk/<id>/approve` and `POST /risk/<id>/reject`, protected by CSRF.
- 404 for an unknown id. Otherwise 403 unless
  `current_user.id == risk.treatment_owner_id`. Admins are not exempt.
- The owner can decide at any time, including flipping an earlier decision or
  re-approving. Each decision is new: it gets a new timestamp and an audit
  event. Self-approval after the owner's own edit is allowed (decision 1058).
- Form fields: `fingerprint` (hidden) and `comment`, which is required for
  reject and has a length limit. If the fingerprint doesn't match, nothing
  changes and the user sees a "risk changed since you opened it" flash and is
  redirected to the edit page.
- Sets the status, `decided_at = now`, `decided_by = current_user` and the
  comment. Logs `risk_approved` or `risk_rejected` through `log_event` with
  the decision, the comment, chance, impact, treatment, residual chance and
  impact, mitigated, actual score and severity, and the fingerprint.
- Comment: up to 2000 characters. On a stale fingerprint the typed comment is
  lost, and the flash says so.
- Closed risks can still be decided. The filter just doesn't list them.

### 12. Edit-page approval panel (`risk/templates/risk/form.html`)
- A panel at the top shows the state pill, who decided and when, and the
  comment.
- When the viewer is the owner, it shows Approve and Reject, each a separate
  small form posting to the routes above. It's shown for manual and
  threat-linked risks alike.
- With no owner: "Assign an owner to request approval."
- With no current decision but an earlier rejection in the audit log (the
  latest `risk_rejected` AuditLog for this risk), show "Previously rejected by
  X on D: comment". A deleted decider shows as "Unknown user".

### 13. Dashboard (`risk/routes.py::dashboard`, `dashboard.html`)
- `?approval=` takes one of these values, and only lists open risks:
  - `mine`: owner = me, and the status is NULL or `rejected`.
  - `awaiting`: there's an owner, and the status is NULL.
  - `rejected`: the status is `rejected`.

  `awaiting` and `rejected` are for every user. An invalid value is ignored.
  The filter combines with `?bia=`, and the metrics and matrix follow it.
- An approval select (All / Awaiting my approval / Awaiting / Rejected) sits
  next to the BIA filter. The "mine" count follows the active BIA filter.
- Empty state: "No risks match the approval filter."
- Card pill: Awaiting approval / Approved / Rejected / No owner.

### 14. API (`risk/services.py::serialize_risk`)
- Additive, read-only fields: `approval_status`, `approval_decided_at`,
  `approval_decided_by` and `approval_comment`. The API has no approve
  endpoint (see Out of Scope).

## Data Model

```
risk_items
  + approval_status          VARCHAR (risk_approval_status: approved|rejected) NULL
  + approval_decided_at      TIMESTAMPTZ NULL
  + approval_decided_by_id   INTEGER NULL  FK users.id ON DELETE SET NULL
  + approval_comment         TEXT NULL
```

State machine:

```
          assign owner / material change / owner change
   ┌──────────────────────────────────────────────┐
   ▼                                              │
awaiting ──approve──► approved ───────────────────┤
   │                                              │
   └──reject(comment)──► rejected ────────────────┘
(no owner: no decision possible)
```

## API/Interface

- `POST /risk/<id>/approve` with form `fingerprint`, `comment?`.
- `POST /risk/<id>/reject` with form `fingerprint`, `comment` (required).
- `GET /risk/?approval=mine|awaiting|rejected[&bia=...]`.
- `Risk.approval_state -> str` and `Risk.approval_fingerprint() -> str`.
- `serialize_risk()`: the additive approval fields.

## Out of Scope

- Notifications (email or in-app) to owners.
- Approving or rejecting through the REST API.
- A separate accountable owner distinct from the treatment owner.
- Using the BIA's free-text `risk_owner`.
- Approval history in the UI. It's in the audit log only.
- Admin override or delegation.
- Approval state in the admin risk register (a follow-up).
- Blocking self-approval.
- Bulk approval of the existing backlog at rollout.

## Rollout

Release notes must say that every existing risk starts as "awaiting approval"
after the upgrade, and that the migration's downgrade drops the approval data.

## Validation

- pytest: the listener resets on each material field, on an owner change and
  on a mitigated flip. It doesn't reset on a text, ticket or component edit,
  or on a new `mitigated_at` timestamp alone.
- pytest: a reset happens through each write path: form edit, admin edit,
  `apply_payload_to_risk` and `sync_scenario_to_risk`.
- pytest: the audit row of a reset contains the cleared approval fields
  (listener order). There's a PASTA publish write-path reset test.
- pytest: flip and re-approve each create a new decision. Close and reopen
  keep the approval. Unknown ids return 404.
- pytest: approve and reject return 403 for a non-owner and for an admin who
  isn't the owner. Reject needs a comment. A stale fingerprint is refused.
  Audit events are written.
- pytest: `?approval=mine|awaiting|rejected` filtering, alone and combined
  with `?bia=`. The panel shows the earlier rejection reason.
- Migration upgrade and downgrade on the dev DB.
- Translations: new keys in `en.json` and `nl.json`.

## Open Questions

None. The comment length (2000 characters) and the checklist gaps are settled
in `20261118-1058-risk-approval-checklist-gap-resolutions`.

---

# Part 3: Open-Only Workspace, Risk Overview and Collapsible Cards

> Added 2026-11-18 on the same branch. Parts 1 and 2 are implemented. Part 3
> is designed but not yet built.

## Overview

The risk workspace (`/risk/`) shows open risks only. Any risk with
`closed_at` set leaves it: closed by hand, or closed by the threat sync
because its scenario is Accepted or Closed or isn't treated by Mitigate. A
new overview page (`/risk/overview`) lists every risk, open and closed, in a
compact table. On the workspace the risk cards start collapsed, to a single
summary row, and open on click.

## User Stories

- As a risk manager, I want closed risks to leave the workspace, so that the
  cards, metrics and matrix show only live risks.
- As a risk manager, I want an overview of every risk, including closed
  ones, so that I can find and review any risk in one place.
- As a risk manager, I want to reopen a closed manual risk, so that I can
  undo a close.
- As a workspace user, I want risk cards collapsed to one line, so that I
  can scan many risks without scrolling.

## Components

### 15. Open-only workspace (`risk/routes.py::dashboard`, `dashboard.html`)
- The base query adds `Risk.closed_at.is_(None)`. The BIA and approval
  filters apply on top, and the cards, metrics, matrix and `mine_count` all
  follow it.
- Remove the workspace's closed-only UI: the Reopen form on cards and the
  "Closed on" status branch. The Close action on cards stays.
- This amends decision 0830: the matrix no longer shows closed risks, and a
  filtered view no longer shows archived ones.
- **Empty state:** with no filter set and only closed risks in the
  database, the workspace shows "No open risks." with a link to the
  overview. "No risks recorded yet" stays for an empty database.
- **Closing a risk from a card:** the flash message becomes
  'Risk "{title}" closed. You can find it on the Risk overview.' (the
  `risk.flash.archived` key, new text).

### 16. Overview page (`risk/routes.py::overview`, new `templates/risk/overview.html`)
- `GET /risk/overview`, with `@login_required` and `_require_risk_access()`.
- Filters: `status=open|closed|all` (default `all`, unknown values mean
  `all`) and `bia=<id>` (repeatable). Parse the BIA ids the same way the
  workspace does, and share a small helper if it avoids duplicating code.
- Columns:
  - severity pill (actual);
  - title, which links to `risk.edit`;
  - actual score;
  - treatment;
  - owner, or "–";
  - approval pill;
  - BIA names, deduplicated;
  - status: Open, Mitigated, or "Closed on D".
- Order: open first, then closed. Within each group, highest actual score
  first (risks with no score last), then by title, case-insensitive. The
  sort runs in Python.
- Status precedence: closed wins. A closed and mitigated risk shows "Closed
  on D". Dates use `'%d %b %Y'`.
- Empty cells:
  - owner: "–", including when the owner was deleted;
  - BIA: "–";
  - severity: "Severity pending".
- Source: the title cell shows a muted "Threat" or "PASTA" label, and
  nothing for a manual risk.
- Pills: the same severity classes and `approval_pills` mapping and labels
  as the workspace.
- Narrow screens: the table sits in an `overflow-x-auto` wrapper.
- Empty state: "No risks match the filter."
- Links: the workspace header gets a "Risk overview" link, and the overview
  links back to the workspace.

### 17. Collapsible cards (`dashboard.html`)
- `<article class="risk-card">` becomes `<details class="risk-card">`. Its
  `<summary>` row shows:
  - the severity pill;
  - the title;
  - the actual score;
  - the approval pill;
  - the due status pill;
  - the Mitigated pill, when the risk is mitigated.
- The body is the current card content, unchanged.
- Cards start collapsed. "Expand all" and "Collapse all" buttons sit above
  the grid. The page's existing nonce'd script toggles `open` on every card,
  and on load opens the card named by a `#risk-<id>` fragment.
- Without JS, each card still toggles on its own.
- The summary row is one line on wide screens, with the title truncated with
  an ellipsis, and it wraps on narrow screens. The treatment pill, the
  description and the PASTA badge stay in the body. The grid aligns cards to
  the top.
- Expand all and Collapse all only render when there are cards. They are
  `<button type="button">`s with `aria-controls` set to the grid's id.
  `<summary>` gets a `:focus-visible` outline.
- A `#risk-<id>` with no matching card (closed or filtered out) does
  nothing.

### 18. Reopen from the edit page (`form.html`, `risk/routes.py::edit`)
- A closed risk's edit page shows a "Closed on D" banner.
  - **Manual and PASTA risks:** the banner has a Reopen button that posts to
    the existing `risk.reopen` route.
  - **Threat-linked risks** (`linked_scenario` set): no button, and the note
    "Reopens when its threat scenario is reopened."
- The edit route passes `action_form` (`RiskActionForm`) for the CSRF token.
- The banner is the first card on the form, above the approval panel and the
  threat-managed note.
- PASTA risks have no revalidation guard. Republishing also reopens them,
  which already happens.
- A threat-linked risk whose scenario was reopened is re-synced open before
  the page renders, so no banner shows.

## Data Model

No changes. "Closed" stays `risk_items.closed_at IS NOT NULL`.

## API/Interface

- `GET /risk/` now lists open risks only.
- `GET /risk/overview?status=open|closed|all&bia=<id>[&bia=...]` is new.
- The `/api/risks` responses don't change.

## Out of Scope

- Column sorting and per-row actions on the overview.
- Remembering which cards are open across page loads.
- Changing which scenario statuses close a risk (Accepted still closes).
- Pagination of the overview.
- Approval filtering on the overview. Approval is a column only.

## Rollout

Release notes must say that closed and archived risks no longer appear on
the risk workspace, its metrics or its matrix, and can be found on the new
Risk overview page.

## Validation

- pytest: the workspace hides closed risks, both manual and threat-closed.
  The metrics and matrix ignore them. `?bia=` and `?approval=` still work.
- pytest: the overview's `status` filter (open, closed, all, invalid), the
  `bia` filter, the row order and the columns.
- pytest: the edit page of a closed manual risk shows Reopen, and a closed
  threat-linked risk shows the note without the button.
- pytest: the workspace renders `<details class="risk-card">` without `open`,
  plus the Expand all and Collapse all controls.
- Translations: new keys in `en.json` and `nl.json`.
- The checklist resolutions are in decision 1210
  (`checklists/workspace-overview.md`).

## Open Questions

None.
