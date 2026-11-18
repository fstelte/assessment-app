---
type: decision
id: 20261118-0751-risk-mitigated-shows-residual-score
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/risk/models.py
  - scaffold/apps/risk/forms.py
  - scaffold/apps/risk/routes.py
  - scaffold/apps/risk/services.py
  - scaffold/apps/threat/services.py
  - migrations/versions/*
tags: [risk, threat, residual-risk, scoring, migration]
participants: [Ferry Stelte, Claude]
---

# Mitigated risks display the residual score, for synced and manual risks

## Context

The risk workspace shows one score: `impact × chance`. Threat scenarios have
initial *and* residual likelihood and impact. Today, setting a scenario to
status `Mitigated` **closes** its linked risk, so a mitigated risk is never
visible with its remaining (residual) exposure. The user wants the workspace to
show the *actual* risk: residual when mitigated, initial otherwise.

## Options Considered

What counts as "mitigated":
- **A: Scenario status = Mitigated (chosen)**, using the existing status.
- B: Residual values are filled in, whatever the status.
- C: All mitigation actions are completed.

Which risks the rule applies to:
- D: Threat-synced risks only (residual read from the scenario).
- **E: All risks, manual ones too (chosen).**

## Decision

- Because manual risks need it too, the data lives on `Risk`: residual
  impact, residual chance, and a mitigated marker. This needs an Alembic
  migration.
- For synced risks: scenario status `Mitigated` sets the risk's mitigated
  marker and copies the residual likelihood and impact. The risk is **no longer
  closed** on Mitigated. `Accepted` and `Closed` still close it, as today.
- Mitigated scenarios are included in the bulk "sync from threats".
- The **actual score** is the residual score when the risk is mitigated *and*
  has residual values. Otherwise it is the initial score. Severity, the matrix
  position and the dashboard metrics use the actual score.

## Consequences

### Positive
- ✅ One definition of "actual risk" across synced and manual risks.
- ✅ Mitigated threats stay visible with their remaining exposure.

### Negative
- ⚠️ Schema change (migration) on `risk_items`.
- ⚠️ Behaviour change: mitigated scenarios no longer archive their risk.

## Related Decisions

- [[20261118-0750-risk-sync-components-from-assigned-assets]]
