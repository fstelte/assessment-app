---
type: decision
id: 20261118-1039-risk-approval-scope-and-reset
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/risk/routes.py
  - scaffold/apps/risk/services.py
  - scaffold/apps/threat/services.py
tags: [risk, approval, sync]
participants: [Ferry Stelte, Claude]
---

# The approval covers the risk and its treatment, and a material change resets it

## Context

We need to define what an owner's approval covers, and when an earlier
approval stops being valid.

## Options Considered

What is approved:
- **A: The risk assessment and the treatment decision (chosen).**
- B: Only risks with treatment = Accept (formal acceptance).
- C: Only the residual risk after mitigation.

When it is invalidated:
- **A: A material change resets it (chosen).**
- B: Any edit resets it.
- C: It never resets, and stays as a historical record only.

## Decision

- An approval confirms the risk's chance, impact and treatment, plus the
  residual chance, residual impact and mitigated state when they are set.
  This applies to every treatment option.
- Material fields: `chance`, `impact`, `treatment`, `residual_chance`,
  `residual_impact` and whether the risk is mitigated (`mitigated_at` set or
  cleared, not a change of timestamp alone). A change to any of these, from
  the form, the API or the threat sync, clears the approval.
- A change of `treatment_owner_id` also clears it, because the new owner
  hasn't approved.
- Text, tickets, components, controls, impact areas, due date and treatment
  plan don't reset the approval.

## Consequences

### Positive
- ✅ An approval always matches the score and treatment currently shown.
- ✅ Edits to wording don't create approval noise.

### Negative
- ⚠️ The threat sync can silently put risks back to "awaiting approval". The
  audit event needs to show that the approval was reset.
