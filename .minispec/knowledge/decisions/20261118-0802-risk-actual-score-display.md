---
type: decision
id: 20261118-0802-risk-actual-score-display
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/risk/routes.py
  - scaffold/apps/risk/services.py
  - scaffold/apps/risk/templates/risk/dashboard.html
  - scaffold/apps/risk/templates/risk/form.html
tags: [risk, residual-risk, dashboard, matrix]
participants: [Ferry Stelte, Claude]
---

# The actual score is shown first, with the initial score as a hint

## Context

[[20261118-0751-risk-mitigated-shows-residual-score]] defines the "actual"
score. This decision covers how it is shown.

## Options Considered

- **A: The actual score, with an initial → residual hint (chosen).**
- B: The actual score only.

## Decision

- The card's main number and severity pill use `actual_score()`.
- Mitigated risks get a "Mitigated" pill and a small line:
  "Initial: 16 → Residual: 6".
- A mitigated risk with no residual values gets a muted hint:
  "Mitigated – residual not set".
- The matrix places each risk at `(actual_chance, actual_impact)`, and its chip
  shows the actual score.
- The "high" metric counts by actual severity.
- `serialize_risk` (API) adds `residual_impact`, `residual_chance`,
  `residual_score`, `mitigated_at` and `actual_score`. Existing `score` and
  `severity` keep their current meaning (initial), so API clients don't break.
  `actual_severity` is added alongside them.

## Consequences

### Positive
- ✅ What the user sees is the current exposure, and the history is still
  visible.

### Negative
- ⚠️ The API now has two scores (`score` and `actual_score`). Document it.
