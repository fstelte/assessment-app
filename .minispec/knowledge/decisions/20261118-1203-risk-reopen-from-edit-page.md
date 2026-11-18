---
type: decision
id: 20261118-1203-risk-reopen-from-edit-page
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/risk/templates/risk/form.html
  - scaffold/apps/risk/routes.py
tags: [risk, closed, ui]
participants: [Ferry Stelte, Claude]
---

# Closed manual risks are reopened from their edit page

## Context

Closed risks leave the workspace, which was where the Reopen button lived.

## Options Considered

- **A: A Reopen button on the edit page, reached from the overview (chosen).**
- B: A Reopen button on each closed row of the overview.

## Decision

- The edit page of a closed risk shows a "Closed on D" banner.
  - **Manual and PASTA risks:** the banner also has a Reopen button that
    posts to the existing `risk.reopen` route.
  - **Threat-linked risks:** the banner says the risk reopens when its
    scenario is reopened, and there's no button. Opening the edit page
    already syncs the risk from its scenario, so a manual reopen would be
    undone immediately.
- `risk.reopen` and `risk.close` redirect back to the page they came from,
  as they already do.

## Consequences

### Positive
- ✅ No new routes. The overview stays read-only.
- ✅ A threat-linked risk can't be reopened by hand only to be closed again
  by the sync.

### Negative
- ⚠️ Reopening takes two clicks: overview → edit → Reopen.
