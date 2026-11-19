---
type: decision
id: 20261119-0741-threat-synced-risk-components-read-only-list
date: 2026-11-19
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/risk/templates/risk/form.html
tags: [risk, threat, sync, ui]
participants: [Ferry Stelte, Claude]
---

# Threat-linked risks show their components as a read-only list

## Context

When a risk is linked to a threat scenario, `edit()` re-syncs it on every visit,
and `mark_managed_by_threat()` disables `component_ids`. Components come only
from the scenario's threatened assets
([[20261118-0750-risk-sync-components-from-assigned-assets]],
[[20261118-0830-risk-residual-checklist-gap-resolutions]]).

## Options Considered

- **A: Read-only list (chosen).** The list has no × buttons and no Add button.
  A note sends the user to the scenario's threatened assets.
- B: Allow components on top of the synced ones. Rejected because the sync
  would have to track which components were added by hand, which changes the
  data model and decision 0750.

## Decision

On a threat-linked risk, the picker shows the synced components as a plain
list. A short note links to the linked scenario. That is the **detail** page,
not the edit page (see [[20261119-0800-asset-picker-checklist-gap-resolutions]]).
From there editors can open the edit page and change the threatened assets.

## Consequences

### Positive
- ✅ The sync stays the single source of truth for these risks.

### Negative
- ⚠️ To change a synced risk's components, the user has to go to the scenario.

## Related Decisions

- [[20261119-0740-affected-assets-list-with-add-overlay]]
- [[20261119-0800-asset-picker-checklist-gap-resolutions]]
