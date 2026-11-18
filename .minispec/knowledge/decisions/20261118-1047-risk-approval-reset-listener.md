---
type: decision
id: 20261118-1047-risk-approval-reset-listener
date: 2026-11-18
status: superseded
supersedes: null
superseded_by: 20261118-1057-risk-approval-reset-before-flush
impacts:
  - scaffold/apps/risk/models.py
tags: [risk, approval, sqlalchemy]
participants: [Ferry Stelte, Claude]
---

# A Risk before_update listener resets the approval

## Context

Five paths write material risk fields: the risk form, the admin register
edit, the API `apply_payload_to_risk`, `sync_scenario_to_risk` and PASTA
publish. Decision 20261118-1039 requires each of them to reset the approval.

## Options Considered

- **A: A SQLAlchemy `before_update` listener on Risk (chosen).**
- B: An explicit helper called from each write path.

## Decision

- `event.listen(Risk, "before_update", _reset_approval_on_material_change)`,
  registered in `risk/models.py`. It follows the BIA `_update_last_modified`
  pattern.
- It uses `sa.inspect(risk).attrs.<f>.history` for `chance`, `impact`,
  `treatment`, `residual_chance`, `residual_impact` and `treatment_owner_id`.
  For mitigated, it compares `bool(old mitigated_at)` with `bool(new)`.
- An attribute that was assigned but whose value didn't change doesn't count.
  The comparison is on values, not just on `has_changes()` with identical
  values.
- When any of them changed, the four approval columns are set to NULL. The
  generic audit before_flush records the change.

## Consequences

### Positive
- ✅ Covers every current and future write path, with no call sites to forget.

### Negative
- ⚠️ Implicit behaviour. It needs a docstring and a test for each write path.
- ⚠️ Bulk `query.update()` bypasses the listener. None of those are used on
  these fields today.
