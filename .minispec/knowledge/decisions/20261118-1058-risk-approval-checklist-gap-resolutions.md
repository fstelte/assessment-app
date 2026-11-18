---
type: decision
id: 20261118-1058-risk-approval-checklist-gap-resolutions
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/risk/routes.py
  - scaffold/apps/risk/templates/risk/dashboard.html
  - scaffold/apps/risk/templates/risk/form.html
  - scaffold/apps/threat/services.py
  - tests/test_risk_approval.py
tags: [risk, approval, checklist]
participants: [Ferry Stelte, Claude]
---

# Resolutions for the risk approval checklist gaps

## Context

`checklists/approval.md` (CHK001–CHK023) found gaps in Part 2. The engineer
decided the items that needed a judgement call (marked *engineer*). The rest
take the proposed default.

## Decision

**Transitions** *(engineer)*
- CHK001/002: the owner can approve or reject at any time, including flipping
  an earlier decision or re-approving. Each decision overwrites the four
  columns with a new timestamp and writes its own audit event.
- CHK003: closing and reopening don't affect the approval.
- CHK014: closed risks can be decided and show their pill. The
  `?approval=...` filters only list open risks.

**Self-approval** *(engineer)*
- CHK015: allowed and documented. The owner is accountable either way. The
  audit trail shows both the owner's edit and their approval.

**Managers** *(engineer)*
- CHK005: `?approval=` accepts `mine`, `awaiting` and `rejected`. `awaiting`
  and `rejected` are open to every authenticated user, which matches the
  dashboard's existing visibility. `awaiting` excludes risks with no owner.
  An invalid value is ignored.
- CHK004: when a risk has no current decision, the edit-page panel shows the
  last rejection: the latest `AuditLog` with `event_type = "risk_rejected"`
  for `target_type = "risk"` and `target_id = <id>`, using the existing
  `ix_audit_logs_target` index. It's labelled "Previously rejected by X on D:
  comment". If the audit log is disabled, nothing is shown.

**Defaults**
- CHK006: the admin risk register doesn't show the approval state. It's out of
  scope and listed as a follow-up.
- CHK007: the toggle count follows the active BIA filter.
- CHK008: a decider whose account was deleted shows as "Unknown user".
- CHK009: `approval_decided_at` is shown in the date format the risk pages
  already use.
- CHK010: stale-fingerprint check: compare the posted fingerprint with
  `approval_fingerprint()`. On a mismatch, redirect to edit with a flash. The
  comment the owner typed is lost; the flash text says so.
- CHK011: the comment limit is 2000 characters. design.md's open question is
  closed.
- CHK012: Task 11 gets a write-path test for
  `publish_pasta_conclusion_to_risk`.
- CHK013: the fingerprint fields and the reset fields are one shared constant
  tuple, `APPROVAL_MATERIAL_FIELDS`, plus the mitigated flag.
- CHK016: an unknown risk id returns 404, as the other risk routes do. That
  check runs before the owner check.
- CHK017: deleting a user sets `treatment_owner_id` to NULL in the DB, which
  bypasses the listener. `approval_state` checks the owner first, so the risk
  shows "No owner". Assigning a new owner (NULL → X) resets the stale
  decision.
- CHK018: a reset caused by the sync is recorded by the generic audit
  (actor = the user who triggered it). `risk_synced_from_threat` details also
  get `approval_reset: bool`.
- CHK019: `risk_approved` and `risk_rejected` details are: `decision`,
  `comment`, `chance`, `impact`, `treatment`, `residual_chance`,
  `residual_impact`, `mitigated`, `actual_score`, `actual_severity`,
  `fingerprint`.
- CHK020: no bulk approval at rollout. The release notes say every risk
  starts as awaiting.
- CHK021: empty state: "No risks match the approval filter."
- CHK022: NL wording: Goedkeuren, Afwijzen, Wacht op goedkeuring,
  Goedgekeurd, Afgewezen, Geen eigenaar.
- CHK023: Task 13's acceptance is a pytest render check. The browser check is
  extra, not the evidence.

## Consequences

### Positive
- ✅ Every checklist item has a decision. There are no open questions left.

### Negative
- ⚠️ The "previously rejected" reason depends on the audit log being enabled.
