---
type: checklist
domain: general
feature: 20260829-095929-description-adr-https
created: 2026-08-29
status: completed
---

# General Requirements Quality Checklist

**Purpose:** Validate that the ADR / Architecture Principle requirements in `design.md` are complete, clear, consistent, measurable, and cover the relevant scenarios — before implementation starts.
**Feature:** Architecture Decision Records on the System Security Plan

## Completeness

- [x] CHK001 - Are audit-logging requirements defined for principle CRUD, principle import, and ADR status changes, given the constitution's Security & Auditability principle requires "explicit role checks and audit visibility" for admin controls? [Gap — not mentioned anywhere in design.md] → Fixed: added FR-012, requiring `log_event()` on all principle mutations and all ADR create/status-change actions.
- [x] CHK002 - Are the allowed ADR status transitions explicitly enumerated (e.g. can Proposed go directly to Superseded? can Accepted go to Rejected?), rather than just the list of possible status values (FR-007)? [Completeness] → Fixed: FR-007 now enumerates every allowed transition and states the terminal states explicitly.
- [x] CHK003 - Does the design specify what happens to an Architecture Principle's `description` on a bulk-import update when the incoming description differs from the stored one — overwrite, merge, or reject? [Gap, FR-002] → Fixed: FR-002 now states overwrite (last-write-wins), plus duplicate-in-file handling.
- [x] CHK004 - Are localization/i18n requirements stated for ADR and Principle admin UI copy and import error messages, per the constitution's Consistent UI and Localization principle? [Gap] → Fixed: added FR-013 requiring `lazy_gettext`/`gettext` routing for all new UI strings.
- [x] CHK005 - Is there a stated requirement for how the primary-principle "immutable after creation" rule (FR-004) is enforced — server-side validation on edit, a read-only field, or both? [Completeness] → Fixed: FR-004 now specifies both (form omits the field; route rejects any attempt to change it regardless of payload).
- [x] CHK006 - Are catalogue/list performance or pagination requirements defined for the Architecture Principle admin list and the SSP's ADR list, given SC-001 anticipates 50+ imported principles? [Gap] → Fixed: added FR-010 pagination requirement, citing the exact existing pattern (`scaffold/apps/admin/routes.py:198`).
- [x] CHK007 - Does the design state what happens to Architecture Principles that become unreferenced after their only referencing ADR is deleted via SSP cascade delete (FR-009) — are they now deletable, and is that consistent with the delete-guard in FR-003? [Completeness] → Fixed: FR-003 now states the guard is evaluated dynamically at delete time, so this resolves itself with no stale window.
- [x] CHK008 - Is concurrent-import behavior specified (e.g. two admins uploading principle files at the same time), or is single-writer assumed without stating so? [Gap] → Fixed: added an explicit "out of scope / accepted assumption" note in Open Questions (last-commit-wins, consistent with the rest of the app).

## Clarity

- [x] CHK009 - Is "the existing catalogue-owner role" in FR-011 quantified with a specific, named role identifier, rather than left as a general reference? [Clarity, FR-011] → Fixed: FR-011 now names `admin` / `ROLE_CONTROL_OWNER` explicitly (verified against `scaffold/apps/identity/models.py` and `_require_control_admin()`).
- [x] CHK010 - Is "immediately on save" (Open Questions, supersession trigger) resolved as a firm requirement rather than left as an assumption pending revisit? [Clarity, Open Questions] → Fixed: promoted into FR-008 as a firm requirement; Open Questions entry marked Resolved.
- [x] CHK011 - Is "case-insensitive `name`" for principle upsert (FR-002) precise about normalization rules (e.g. leading/trailing whitespace, Unicode case-folding), or does it leave edge cases to implementer judgment? [Clarity] → Fixed: FR-002 now specifies trim + Unicode casefold.
- [x] CHK012 - Is "reviewer" in User Story 4 defined in terms of an actual role/permission, or is it an informal persona without a corresponding access-control requirement? [Clarity] → Fixed: User Story 4 now clarifies "reviewer" = any authenticated user with existing SSP view access, no new role.

## Consistency

- [x] CHK013 - Is the hard-delete-with-use-guard behavior decided for Architecture Principles (Open Questions) consistent with how the Control catalogue actually behaves today, or was that assumption verified against current Control delete behavior rather than only against the design intent? [Consistency] → **Real inconsistency found and fixed.** `delete_control()` (`scaffold/apps/admin/routes.py:425-455`) has no use-guard at all — it deletes unconditionally and cascades to `AssessmentTemplate`. The design's claim that the principle guard "mirrors current Control behavior" was false. FR-003 now documents the deliberate deviation and why (ADR references are compliance records, unlike disposable `AssessmentTemplate` rows); Open Questions and the decision record no longer make the false claim.
- [x] CHK014 - Do the cascade-delete requirements for ADRs-under-SSP (FR-009) and the deletion guard for Principles-referenced-by-ADR (FR-003) agree on what happens in the compound case (SSP deleted → ADRs cascade-deleted → principle references drop) without leaving a window where a principle appears both "in use" and "deletable"? [Consistency] → Fixed by the same FR-003 edit as CHK007: the guard is dynamic, so no window exists.
- [x] CHK015 - Does the terminology stay consistent between "Architecture Principle catalogue" (admin-facing) and "principle picker" (ADR-authoring UX) so the same concept isn't described with drifting names across the user stories and functional requirements? [Consistency] → Reviewed: terminology is consistent throughout (`Architecture Principle` for the catalogue entity, `primary`/`secondary principle` for ADR linkage, no drift found); no change needed.

## Measurability

- [x] CHK016 - Can SC-002 ("0% of saved ADRs have a null primary principle") be objectively verified, and does the design state whether this is enforced at the database (NOT NULL) or only at the form-validation layer? [Measurability, SC-002] → Fixed: SC-002 now states both the DB `NOT NULL` constraint and the form-level check.
- [x] CHK017 - Is SC-003 ("100% of ADRs marked Superseded have a resolvable link") verifiable through an automated check (e.g. a query/test), or does it depend on manual inspection? [Measurability] → Fixed: SC-003 now points to the specific pytest task (tasks.md Task 11) that asserts this automatically.
- [x] CHK018 - Is SC-001's "under a minute" import benchmark tied to a specific environment/dataset size, or is it an unqualified claim that can't be objectively measured? [Measurability, SC-001] → Fixed: SC-001 now references the concrete example file / dataset size and the pytest task that verifies it.

## Coverage

- [x] CHK019 - Does the design address what a user sees when they attempt to create an ADR while the Architecture Principle catalogue is empty, beyond "a message directing them to ask an admin" (User Story 3, Scenario 3) — is the exact message/behavior specified for non-admin vs admin viewers? [Coverage] → Fixed: added FR-014 specifying the exact non-admin vs admin empty-state behavior (admin sees a direct link to `/admin/principles`).
- [x] CHK020 - Are error/failure states covered for the "supersedes" picker itself — e.g. what happens if the ADR chosen to be superseded belongs to a different SSP (should be impossible per FR-008, but is the rejection behavior specified)? [Edge Case, FR-008] → Fixed: FR-008 now requires the picker be scoped to same-SSP ADRs and requires server-side rejection (not just UI prevention) of a cross-SSP or already-superseded target.
- [x] CHK021 - Does the design cover what happens to an ADR's status display when it is simultaneously "Deprecated" by direct status change and referenced as `supersedes` by a newer ADR — is there a defined precedence between the two? [Edge Case, FR-007/FR-008] → Fixed: FR-007/FR-008 now make the two states mutually exclusive by construction (Superseded is reachable only via the supersede action, never a direct manual edit), so the conflict cannot occur.
- [x] CHK022 - Are requirements defined for exporting or printing ADRs as part of the SSP (since SSPs typically support export elsewhere in the app), or is export explicitly out of scope? [Coverage] → Fixed: added an explicit "Out of scope" entry in Open Questions.

## Summary

- **Total Items:** 22
- **Resolved:** 22 / 22
- **Focus Areas:** Completeness (8), Clarity (4), Consistency (3), Measurability (3), Coverage (4)
- **Notable finding:** CHK013 surfaced a genuine factual error in the design, not just a documentation gap — the claim that the Architecture Principle delete-guard "mirrors current Control behavior" was false (Control has no delete-guard and cascades instead). Corrected in `design.md` FR-003 and the Open Questions section.
- All other items were completeness/clarity/consistency/measurability gaps closed by adding FR-002 through FR-014 detail, firming up Open Questions, and tightening Success Criteria — no further design changes pending from this checklist. See `design.md` for the updated requirements and `tasks.md` for the implementation breakdown that now reflects FR-012/FR-013/FR-014 (Tasks 5, 6, 8, 9, 10, 11).
