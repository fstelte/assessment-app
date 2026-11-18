---
type: decision
id: 20261118-1200-risk-workspace-hides-closed-risks
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
amends: 20261118-0830-risk-residual-checklist-gap-resolutions
impacts:
  - scaffold/apps/risk/routes.py
  - scaffold/apps/risk/templates/risk/dashboard.html
tags: [risk, workspace, closed]
participants: [Ferry Stelte, Claude]
---

# The risk workspace shows open risks only

## Context

A risk is closed when `closed_at` is set. That happens through the manual
Close button, or the threat sync when a scenario becomes Accepted or Closed
or its treatment isn't Mitigate. Closed risks still showed on the workspace
with a "Closed on" label, and they counted in the matrix and the metrics.
The engineer wants them gone from the workspace.

## Options Considered

- **A: Hide every risk with `closed_at` set (chosen).**
- B: Only hide risks whose scenario status is Closed. This would mean
  changing the sync so Accepted keeps the risk open.

## Decision

- `risk.dashboard` filters `Risk.closed_at IS NULL` before building the
  cards, metrics and matrix. The BIA and approval filters apply on top.
- This amends decision 0830 in two places: "the matrix keeps showing closed
  risks" and "archived risks are still shown under a filter" no longer hold
  for the workspace.
- The threat sync stays as it is. Accepted, Closed and non-mitigate
  scenarios still close their risk, and a scenario that reopens still
  reopens the risk.
- The workspace cards no longer need their Reopen button. Closing a risk
  from a card removes it from the workspace.

## Consequences

### Positive
- ✅ One rule (`closed_at`) for manual and threat-linked risks alike.
- ✅ The metrics and matrix show the live risk picture.

### Negative
- ⚠️ Closed risks are only visible on the overview page (decision 1201).
