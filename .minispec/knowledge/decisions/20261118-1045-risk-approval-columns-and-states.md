---
type: decision
id: 20261118-1045-risk-approval-columns-and-states
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/risk/models.py
  - migrations/versions/
  - scaffold/core/audit.py
tags: [risk, approval, data-model]
participants: [Ferry Stelte, Claude]
---

# Approval state lives in columns on risk_items, with approve or reject

## Context

We need to store the owner's approval or rejection. History can come from the
audit log, which already tracks Risk field changes (`core/audit.py`).

## Options Considered

Storage:
- **A: Columns on `risk_items` (chosen).**
- B: A separate `risk_approvals` table with snapshots, like
  `MaturityAssessmentVersion`.

Owner actions:
- **A: Approve, or reject with a required comment (chosen).**
- B: Approve only.

## Decision

New nullable columns on `risk_items`:
- `approval_status`: `NULL` (awaiting approval), `approved` or `rejected`.
  Stored as a string enum, `RiskApprovalStatus`.
- `approval_decided_at`: TIMESTAMPTZ.
- `approval_decided_by_id`: FK `users.id`, `ON DELETE SET NULL`.
- `approval_comment`: TEXT. Required when rejecting, optional when approving.

A reset sets all four back to NULL. The four fields are added to the Risk
entry in the audit model registry, so approvals, rejections and resets show up
in the audit trail.

## Consequences

### Positive
- ✅ One migration and no new model. It's easy to filter and display.
- ✅ The history comes from the audit log, which already exists.

### Negative
- ⚠️ The UI shows only the latest decision. Past approvals are visible only
  in the audit log.
- ⚠️ Existing risks start as "awaiting approval" after the upgrade.
