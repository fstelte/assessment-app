---
type: decision
id: 20261118-1046-risk-approval-owner-only
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/risk/routes.py
tags: [risk, approval, authorization, security]
participants: [Ferry Stelte, Claude]
---

# Only the assigned owner can approve or reject

## Context

Constitution principle II requires explicit role checks for changes to who
can act on data. The maturity flow also lets admins approve. Risk routes today
only check that the user is logged in.

## Options Considered

- **A: Only the owner (chosen).**
- B: The owner or an admin.

## Decision

- `POST /risk/<id>/approve` and `/reject` return 403 unless
  `current_user.id == risk.treatment_owner_id`. Admins are not exempt.
- A risk with no owner can't be decided. The panel says that an owner has to
  be assigned first.
- Admins and risk managers can still reassign the owner, which resets the
  approval.
- Stale-view guard: the decision form posts a fingerprint of the material
  fields. If it no longer matches, the decision is refused with "risk changed
  since you opened it, review again".

## Consequences

### Positive
- ✅ Clear segregation of duties, and an approval always comes from the
  accountable person.

### Negative
- ⚠️ If an owner leaves, their risks stay undecided until someone reassigns
  them.
