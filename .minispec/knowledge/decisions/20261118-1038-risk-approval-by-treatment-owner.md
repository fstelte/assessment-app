---
type: decision
id: 20261118-1038-risk-approval-by-treatment-owner
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/risk/models.py
  - scaffold/apps/risk/routes.py
tags: [risk, approval, ownership]
participants: [Ferry Stelte, Claude]
---

# The risk's treatment owner is the approver

## Context

Risk owners need to approve the risks they own. The codebase has two "owner"
concepts. `Risk.treatment_owner_id` is a user FK, labelled "Owner" on the risk
form. `ContextScope.risk_owner` on a BIA is free text and can't be matched to a
logged-in user.

## Options Considered

- **A: Reuse `Risk.treatment_owner_id` (chosen).**
- B: Add a new `risk_owner_id`, separate from the treatment owner
  (accountable vs responsible).
- C: Turn the BIA's free-text `risk_owner` into a user FK and use it for every
  risk on the BIA's components.

## Decision

The user in `Risk.treatment_owner_id` is the risk owner for approval. A risk
with no owner can't be approved until an owner is assigned.

## Consequences

### Positive
- ✅ No new ownership field and no data migration for owners.
- ✅ Matches the "Owner" label users already see.

### Negative
- ⚠️ Accountability and execution can't be split between two people. If this
  is needed later, option B is the follow-up.
- ⚠️ The BIA's free-text `risk_owner` stays unrelated to risk approval.
