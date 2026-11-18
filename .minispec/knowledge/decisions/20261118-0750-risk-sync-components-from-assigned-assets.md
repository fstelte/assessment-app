---
type: decision
id: 20261118-0750-risk-sync-components-from-assigned-assets
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/threat/services.py
  - scaffold/apps/risk/routes.py
tags: [risk, threat, sync, components]
participants: [Ferry Stelte, Claude]
---

# Risk sync links only the components a scenario lists as threatened

## Context

`_components_for_scenario()` resolves the BIA components for a synced risk. It
looks only at the legacy single `ThreatScenario.asset`. When that is empty or
has no name match, it falls back to **every** component in the threat model's
BIA (`context_scope_id`). Scenarios already have a plural `assigned_assets` list
(the "Threatened assets" field), and the sync ignores it. So risks in the risk
workspace pick up components the threat model never marked as affected.

## Options Considered

When nothing matches (no assets selected, or no BIA component with that name):

- **A: Link no components (chosen).** Link only what matches.
- B: Skip the sync until at least one asset matches.
- C: Keep whatever components the risk already has.

## Decision

- Components come from `scenario.assigned_assets`. If that list is empty, the
  legacy `scenario.asset` is used instead.
- Each asset is matched by name to a `Component` in the threat model's
  `context_scope_id`. Eligibility is not required, as today.
- Remove the "all components in the BIA" fallback. If nothing matches, the risk
  gets an empty component list.
- This applies everywhere `_components_for_scenario` is used: scenario
  create/update, the per-scenario sync, the bulk "sync from threats", and the
  re-sync in the risk edit view.

## Consequences

### Positive
- ✅ Synced risks show exactly the components the threat model says are affected.
- ✅ Respects the plural asset assignment that was built for this.

### Negative
- ⚠️ A synced risk can have zero components. The manual risk form requires at
  least one, so editing such a risk through the form needs the requirement
  relaxed for threat-linked risks, or the user has to add one.
- ⚠️ Existing synced risks that got the fallback will lose components on the
  next sync. This is intended, but it is a visible change.

## Related Decisions

- [[20261118-0751-risk-mitigated-shows-residual-score]]
