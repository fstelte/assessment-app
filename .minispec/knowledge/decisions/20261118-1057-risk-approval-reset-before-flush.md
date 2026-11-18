---
type: decision
id: 20261118-1057-risk-approval-reset-before-flush
date: 2026-11-18
status: accepted
supersedes: 20261118-1047-risk-approval-reset-listener
superseded_by: null
impacts:
  - scaffold/apps/risk/models.py
  - scaffold/core/audit.py
tags: [risk, approval, sqlalchemy, audit]
participants: [Ferry Stelte, Claude]
---

# The approval reset runs in a session before_flush listener, ahead of the audit

## Context

Decision 1047 chose a mapper `before_update` listener. `/minispec.analyze`
found that the generic audit (`core/audit.py::_before_flush`) captures field
changes in the session's `before_flush`, which runs **before** mapper
`before_update`. Approval fields cleared there would never reach the audit
diff. That breaks decision 1045 and constitution principle II.

## Options Considered

- **A: A session `before_flush` listener registered with `insert=True` (chosen).**
- B: Keep `before_update` and write a dedicated audit row from inside the
  flush.

## Decision

- `event.listen(db.session, "before_flush", _reset_risk_approvals, insert=True)`.
  `insert=True` puts it ahead of the audit listener, whatever the
  registration order.
- It iterates `session.dirty` for `Risk` instances, skipping new and deleted
  ones. It uses the same value comparison as 1047: material fields,
  `treatment_owner_id`, and the mitigated flag flip. When any of them changed,
  it clears the four approval columns.
- The audit's `_capture_update` then sees the cleared fields as part of the
  same change set.
- Registered once, guarded the same way as the audit's
  `auto_listener_registered`, so test app factories don't register it twice.

## Consequences

### Positive
- ✅ Resets show up in the audit trail with no extra code.
- ✅ Still covers every ORM write path.

### Negative
- ⚠️ A session-level listener runs on every flush. The cost is an
  isinstance filter over `session.dirty`, which is negligible.
- ⚠️ It depends on listener order. A test asserts that the audit row contains
  the cleared fields.
