---
type: decision
id: 20261118-1201-risk-overview-table
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/risk/routes.py
  - scaffold/apps/risk/templates/risk/overview.html
  - scaffold/translations/en.json
  - scaffold/translations/nl.json
tags: [risk, overview, ui]
participants: [Ferry Stelte, Claude]
---

# A compact overview table lists every risk, open and closed

## Context

Once the workspace hides closed risks (decision 1200), users still need one
place to see every risk.

## Options Considered

- **A: A compact table of all risks with filters (chosen).**
- B: A table with column sorting and a Reopen button on each row.
- C: The workspace's card and matrix layout with closed risks included.

## Decision

- `GET /risk/overview`, with the same access check as the workspace.
- One row per risk. Columns:
  - severity (actual);
  - title, which links to `risk.edit`;
  - actual score;
  - treatment;
  - owner;
  - approval state;
  - BIA(s);
  - status: open, closed with its date, or mitigated.
- Filters, all in the URL: `status=open|closed|all` (default `all`) and
  `bia=` (repeatable, the same as the workspace).
- Approval is a column only, with no `?approval=` on the overview. The
  approval filters only list open risks (decision 1058), so they would clash
  with `status=closed`. Approval filtering stays on the workspace.
- Order: open risks first, then closed. Within each group, highest actual
  score first.
- The workspace header links to the overview, and the overview links back.

## Consequences

### Positive
- ✅ Every risk is visible in one place, closed ones included.
- ✅ Reuses the workspace's filter parsing.

### Negative
- ⚠️ No pagination. That's acceptable for the current number of risks;
  revisit if it reaches the hundreds.
