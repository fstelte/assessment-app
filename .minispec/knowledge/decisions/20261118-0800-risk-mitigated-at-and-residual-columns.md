---
type: decision
id: 20261118-0800-risk-mitigated-at-and-residual-columns
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/risk/models.py
  - scaffold/apps/risk/forms.py
  - scaffold/apps/risk/services.py
  - scaffold/apps/threat/services.py
  - migrations/versions/*
tags: [risk, residual-risk, schema, migration]
participants: [Ferry Stelte, Claude]
---

# Risk stores `mitigated_at` plus residual impact and chance

## Context

[[20261118-0751-risk-mitigated-shows-residual-score]] puts residual values and a
mitigated marker on `Risk`. This decision picks their shape.

## Options Considered

- **A: `mitigated_at` nullable timestamp (chosen).** Same pattern as `closed_at`.
- B: `is_mitigated` boolean.
- C: A status enum (open/mitigated/closed) that replaces `closed_at`.

## Decision

New nullable columns on `risk_items`, in one Alembic migration:
- `mitigated_at` (`DateTime(timezone=True)`)
- `residual_impact` (`risk_impact` enum, same values as `impact`)
- `residual_chance` (`risk_chance` enum, same values as `chance`)

Model helpers:
- `is_mitigated`: `mitigated_at is not None`.
- `residual_score()`: `IMPACT_WEIGHTS[residual_impact] * CHANCE_WEIGHTS[residual_chance]`,
  or `None` if either value is missing.
- `actual_score()`: `residual_score()` when the risk is mitigated and both
  residual values are set. Otherwise `score()`.
- `actual_chance` / `actual_impact`: the matching pair, used to place the risk
  in the matrix.

Sync (threat → risk): scenario status `Mitigated` sets `mitigated_at`. It keeps
an existing timestamp and otherwise uses now. It copies `residual_likelihood`
and `residual_impact` through the existing `_CHANCE_MAP` and `_IMPACT_MAP`. Any
other open status clears `mitigated_at`. The residual values are always copied
when present.

Manual form: a "Mitigated" checkbox plus residual impact and chance selects.
For threat-linked risks, the scenario is the source of truth, as it already is
for chance and impact. The edit view re-syncs these fields.

## Consequences

### Positive
- ✅ Follows the `closed_at` pattern already in the model.
- ✅ Records when a risk was mitigated, for audit and later reporting.

### Negative
- ⚠️ Mitigated but without residual values falls back to the initial score.
  The UI should show that as a gap.
