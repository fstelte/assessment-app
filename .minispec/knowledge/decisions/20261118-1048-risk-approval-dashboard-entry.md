---
type: decision
id: 20261118-1048-risk-approval-dashboard-entry
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/risk/routes.py
  - scaffold/apps/risk/templates/risk/dashboard.html
  - scaffold/apps/risk/templates/risk/form.html
  - scaffold/translations/en.json
  - scaffold/translations/nl.json
tags: [risk, approval, ui]
participants: [Ferry Stelte, Claude]
---

# Owners find pending approvals through a dashboard filter, pills and an edit-page panel

## Context

Owners need to find the risks that are waiting for their decision. The risk
module has no detail page. `risk.edit` is the per-risk view.

## Options Considered

- **A: A dashboard toggle, a card pill and an approval panel on the edit page (chosen).**
- B: A dedicated `/risk/approvals` page.
- C: The edit page only.

## Decision

- `GET /risk/?approval=mine` shows open risks where
  `treatment_owner_id = current_user.id` and `approval_status` is NULL or
  `rejected`. It combines with `?bia=`. The metrics and matrix follow the
  filter, as with the BIA filter.
- Each card gets one pill: "Awaiting approval", "Approved" or "Rejected".
  Risks with no owner get a muted "No owner".
- `risk/form.html` gets an approval panel at the top. It shows the state, who
  decided, when, and the comment. When the viewer is the owner, it also shows
  Approve and Reject buttons, with a comment textarea that is required for
  Reject. This works for threat-linked (read-only) risks too.
- Decisions are posted with CSRF to the dedicated routes, not through the
  edit form.

## Consequences

### Positive
- ✅ Reuses the filter mechanism from 20261118-0801.
- ✅ No new page or navigation entry.

### Negative
- ⚠️ No notification. Owners have to open the filter themselves.
