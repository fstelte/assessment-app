---
type: checklist
domain: security
feature: 20261118-074624-risk-workspace-sync-bia-filter
created: 2026-11-18
status: completed
---

# Risk Owner Approval Requirements Quality Checklist

**Purpose:** Check that the requirements for Part 2 (risk owner approval) are
complete, clear and consistent. The focus is authorization, state transitions
and audit.
**Feature:** 20261118-074624-risk-workspace-sync-bia-filter, Part 2
(decisions 20261118-1038 to -1048)

## Completeness

- [x] CHK001 - Does the design define whether the owner can change a decision
  directly (approved → rejected, rejected → approved) without a material
  change in between? The state machine only shows transitions out of
  "awaiting". [Gap, Design §Data Model]
- [x] CHK002 - Is re-approving an already approved risk defined: allowed (new
  timestamp), a no-op, or refused? [Gap, Design §11]
- [x] CHK003 - Is it defined whether closing or reopening a risk affects its
  approval? Neither is in the material-field list, and neither is explicitly
  excluded. [Gap, Decision 1039]
- [x] CHK004 - Does the design define what the risk manager sees of a
  rejection comment after a material change resets it? The reset clears
  `approval_comment`, so the reason is then only in the audit log. [Gap,
  Decision 1045]
- [x] CHK005 - Is there a requirement for how risk managers find **rejected**
  risks? `?approval=mine` is owner-only, and no rejected filter exists for
  managers. [Gap, Design §13]
- [x] CHK006 - Does the design say whether the admin risk register list and
  edit page show the approval state? [Gap, Design §10/§13]

## Clarity

- [x] CHK007 - Is the count next to the "Awaiting my approval" toggle
  specified: global, or within the active BIA filter? [Clarity, Design §13]
- [x] CHK008 - Is the display defined for a decision whose decider's user
  account was deleted (`approval_decided_by_id` set to NULL)? [Clarity,
  Decision 1045]
- [x] CHK009 - Is the format and timezone of `approval_decided_at` in the UI
  specified, and does it match how other dates are shown on the risk pages?
  [Clarity, Design §12]
- [x] CHK010 - Is "the risk changed since you opened it" defined precisely as
  a mismatch on the fingerprint fields, and is it clear that the comment
  already typed is lost or kept? [Clarity, Decision 1046]

## Consistency

- [x] CHK011 - Is the comment length (2000 characters) consistent between
  design.md, which still lists it as an open question, and tasks.md, which
  resolves it? [Consistency]
- [x] CHK012 - Is PASTA publish, listed as a write path in Decision 1047,
  covered by the validation list in Design §Validation and by Task 11's
  write-path tests? [Consistency]
- [x] CHK013 - Do the fingerprint fields (Task 10) match the reset-listener
  fields (Decision 1047) exactly, including `treatment_owner_id` and the
  mitigated flag? [Consistency]
- [x] CHK014 - Does "closed risks can still be decided" (Design §11) agree
  with the dashboard filter excluding closed risks, and is the card pill for
  closed risks defined? [Consistency, Design §13]

## Security & Authorization

- [x] CHK015 - Does the design address self-approval: an owner who makes a
  material edit themselves, then approves it? Segregation of duties is the
  stated reason for owner-only approval. [Gap, Decision 1046]
- [x] CHK016 - Is the response to an approve or reject on a non-existent
  risk id specified (404 or 403), and is it consistent with the other risk
  routes? [Clarity, Design §11]
- [x] CHK017 - Is the DB-level `ON DELETE SET NULL` on `treatment_owner_id`
  (which the ORM listener doesn't see) addressed? Does a stale `approved`
  status on an ownerless risk always show as "No owner"? [Edge Case,
  Decision 1047]
- [x] CHK018 - Are the audit requirements for a reset caused by the threat
  sync specified (actor, and whether the scenario id appears), so that a
  reviewer can tell why an approval disappeared? [Completeness, Decision
  1039]
- [x] CHK019 - Does the design define which fields the `risk_approved` and
  `risk_rejected` audit events must contain, so they can serve as sign-off
  evidence? [Measurability, Design §11]

## Coverage & Rollout

- [x] CHK020 - Is there a rollout requirement for the backlog of existing
  risks that all become "awaiting approval": none, or a one-off bulk approval
  by owners? [Coverage, Design §Rollout]
- [x] CHK021 - Is the empty-state text defined for `?approval=mine` when the
  user owns no pending risks? [Edge Case, Design §13]
- [x] CHK022 - Are the NL translations of "approve", "reject", "awaiting
  approval" and "no owner" agreed, given the existing risk terminology?
  [Consistency, Constitution IV]
- [x] CHK023 - Can each acceptance criterion in Tasks 10–15 be checked
  objectively, without a subjective browser check (Task 13)? [Measurability]

## Resolution

All 23 items are resolved in
`20261118-1058-risk-approval-checklist-gap-resolutions`. CHK001–005, 014 and
015 were the engineer's decisions. The rest take the proposed defaults. The
design and tasks are updated to match.

`/minispec.analyze` also found the listener ordering issue, settled in
`20261118-1057-risk-approval-reset-before-flush` (supersedes 1047).

## Summary

- **Total Items:** 23
- **Focus Areas:** state transitions (CHK001–004, 014), authorization and
  audit (CHK015–019), manager visibility (CHK005–006), consistency between
  design and tasks (CHK011–013).
- **Key Gaps Identified:**
  - Changing a decision, re-approving and close/reopen are undefined
    (CHK001–003).
  - Self-approval after the owner's own edit (CHK015).
  - Managers can't find rejected risks, and the rejection reason is lost on
    reset (CHK004–005).
  - The PASTA write path is missing from the tests (CHK012).
