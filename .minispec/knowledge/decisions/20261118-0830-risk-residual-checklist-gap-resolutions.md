---
type: decision
id: 20261118-0830-risk-residual-checklist-gap-resolutions
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/threat/services.py
  - scaffold/apps/risk/routes.py
  - scaffold/apps/risk/forms.py
  - scaffold/apps/risk/services.py
  - scaffold/apps/risk/templates/risk/form.html
  - scaffold/apps/risk/templates/risk/dashboard.html
  - scaffold/apps/admin/routes.py
  - scaffold/apps/ssp/routes.py
tags: [risk, threat, residual-risk, audit, checklist]
participants: [Ferry Stelte, Claude]
---

# Resolutions for the risk residual / BIA filter checklist gaps

## Context

`/minispec.checklist` (general) and `/minispec.analyze` found 24 requirement
gaps in the design for `20261118-074624-risk-workspace-sync-bia-filter`. Two of
them were critical:
- Sync changes had no audit trail (Constitution II).
- The admin risk register and the SSP severity summary still used the initial
  score.

## Decisions made by the engineer

- **Other score surfaces:** the admin risk register (`/admin/risks`,
  `/admin/risks/<id>`) and the SSP risk severity summary use the actual score
  and actual severity. Without this, the SSP summary over-counts, because
  mitigated risks no longer close.
- **Audit:** `sync_scenario_to_risk` writes one `risk_synced_from_threat`
  event per risk, and only when something changed. The event records before
  and after values for every changed field:
  - component ids
  - `mitigated`
  - residual impact and chance
  - chance and impact
  - `reopened` and `closed`
  It also records the scenario id. Creating a risk from a scenario logs
  `risk_created_from_threat`.
- **Treatment gate kept:** only scenarios with treatment `Mitigate` feed the
  workspace. Status Mitigated with any other treatment still closes the risk.
- **Linked risks are read-only for synced fields:** in the risk edit form,
  chance, impact, residual impact and chance, Mitigated and components are
  disabled for threat-linked risks, with a "Managed by threat scenario" note
  and link. Posted values for these fields are ignored. The edit GET calls
  `sync_scenario_to_risk` rather than repeating the inline re-sync logic.

## Defaults accepted

- **Name matching:** case-insensitive, with whitespace trimmed, for any
  `AssetType`. If several components in the BIA share a name, all are linked.
  Duplicates are removed by id.
- **Residual without Mitigated:** on manual risks the residual values may be
  saved while Mitigated is unchecked. They are stored but do not affect the
  score. Cards show nothing extra.
- **API:** `mitigated: true` keeps an existing `mitigated_at`. An omitted field
  leaves the value unchanged. An explicit `null` clears the residual field.
- **Closed and mitigated:** both pills are shown and the score is the actual
  score. The matrix keeps showing closed risks, as it does today.
- **PASTA-published risks:** republishing does not touch `mitigated_at` or the
  residual values. A manually set mitigated flag is kept. These risks are not
  scenario-linked, so the form stays editable.
- **Residual higher than initial:** allowed, with no validation. It records
  the assessment as given.
- **Re-mitigation:** when a scenario goes Mitigated → open → Mitigated, the
  second time gets a new `mitigated_at`, because it was cleared on reopen.
- **"Components impacted" under a BIA filter:** counts only components that
  belong to the selected BIAs.
- **Archived risks under a filter:** they are still shown, as in the
  unfiltered view.
- **BIA options:** every BIA that has at least one component. Visibility is
  the same as today: any authenticated user, since BIA names already appear on
  the cards.
- **No BIA on the threat model:** the risk has no components and does not
  appear under any BIA filter.
- **Matrix copy:** the heading and footnote say they show the actual score
  (residual when mitigated).
- **The "mitigate" hero metric** is relabelled "Treatment: mitigate", so it
  isn't confused with the Mitigated state.
- **Exports:** the risk module has none, so there is nothing to change.
- **Rollout:** release notes in the PR and GitHub release must cover two
  things:
  - Synced risks lose the components they got from the old "all components"
    fallback.
  - Archived risks of mitigated scenarios reopen.
  The migration's downgrade drops the residual data.

## Related Decisions

- [[20261118-0750-risk-sync-components-from-assigned-assets]]
- [[20261118-0751-risk-mitigated-shows-residual-score]]
- [[20261118-0800-risk-mitigated-at-and-residual-columns]]
- [[20261118-0801-risk-workspace-bia-multi-filter]]
- [[20261118-0802-risk-actual-score-display]]

## Amendment (2026-11-18, during Task 4)

`sync_scenario_to_risk` also sets title, description, treatment and controls.
So when the edit page calls it, those fields would silently revert as well.
Decision by the engineer:

- **Read-only for threat-linked risks:** everything the sync owns. That is
  title, description, chance, impact, treatment, residual impact and chance,
  Mitigated, components and controls. Posted values for these fields are
  ignored. The component requirement and the "Mitigate needs a control"
  requirement are skipped for linked risks.
- **Still editable:** impact areas, treatment plan, owner, due date, ticket
  links and discovered on.
- This matches the PASTA rule: the risk row is a projection of its source.
