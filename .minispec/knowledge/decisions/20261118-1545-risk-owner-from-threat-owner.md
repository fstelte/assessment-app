---
type: decision
id: 20261118-1545-risk-owner-from-threat-owner
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/threat/services.py
  - scaffold/apps/risk/templates/*
  - scaffold/apps/admin/templates/admin/_risk_form.html
  - tests/test_threat_risk_sync.py
tags: [risk, threat, sync, owner, approval]
participants: [Ferry Stelte, Claude]
---

# The owner defined on a threat becomes the risk owner on sync

## Context

`sync_scenario_to_risk` copies title, description, scores, treatment, the
mitigated marker, residual scores, components and controls from a
`ThreatScenario` to its linked `Risk`. It never copies the owner, so
`Risk.treatment_owner_id` is only ever set by hand, even though the threat
already says who owns the scenario. Two threat-side owners exist:
`ThreatScenario.owner_id` and `ThreatModel.owner_id`. PASTA conclusions
(`publish_pasta_conclusion_to_risk`) have no owner of their own.
`treatment_owner_id` is in `APPROVAL_MATERIAL_FIELDS`, so changing it resets an
owner decision (decisions 20261118-1039, -1057).

## Options Considered

Source: scenario owner with model fallback / scenario owner only / model owner
only.
Authority on re-sync: overwrite with the field locked / overwrite but
editable / fill only when empty.

## Decision

- **Source: the scenario owner, otherwise the model owner.**
  `risk.treatment_owner_id = scenario.owner_id or scenario.threat_model.owner_id`.
  When a PASTA conclusion publishes a risk, the conclusion's threat model
  owner is used.
- **Authority: overwrite on every sync, but keep the field editable.** Create
  and each re-sync set the owner from the threat. If neither threat owner is
  set, the risk owner is cleared. This makes the threat the source, as it
  already is for components and scores. Users can still change the owner on
  the risk edit pages (`risk.edit`, `admin.risk_edit`). For threat-linked
  risks the owner select gets the hint "Set from the threat owner; the next
  threat sync overwrites this", so the overwrite is not a surprise.
- **Approval:** no new rule. An owner change made by sync resets the owner
  decision through the existing listener, as any other material change does.
  The sync audit already reports `approval_reset`.
- **Audit:** add `treatment_owner_id` to `_risk_sync_snapshot`, so
  `risk_created_from_threat` / `risk_synced_from_threat` record owner changes.
- **Not a backfill:** existing linked risks pick up the threat owner at their
  next sync (scenario save, per-scenario sync or the bulk "sync from threats").
  No migration is needed.

## Consequences

### Positive
- ✅ Risks from threats have an owner right away, so owner approval can start
  without manual work
- ✅ No schema change

### Negative
- ❌ A manual owner change on a threat-linked risk is lost at the next sync
  (made visible by the hint)
- ❌ A sync that changes the owner resets an existing approval
- ❌ Clearing the threat owner clears the risk owner
