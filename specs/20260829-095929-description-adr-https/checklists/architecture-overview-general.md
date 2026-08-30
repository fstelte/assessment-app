---
type: checklist
domain: general
feature: 20260829-095929-description-adr-https (Architecture Overview Image)
created: 2026-08-29
status: draft
---

# General Requirements Quality Checklist — Architecture Overview Image

**Purpose:** Validate that the Architecture Overview Image requirements (design.md's
second feature section) are complete, clear, consistent, and measurable before
implementation starts.
**Feature:** Architecture Overview Image on the SSP

## Completeness

- [x] CHK001 - Is the authorization requirement for the image-serving route (`GET .../image`) stated explicitly as its own requirement, rather than only appearing in the Design Notes' route list? [Gap, Design Notes vs FR-001] — **Resolved**: FR-001 extended to explicitly cover restore and image-serving routes.
- [x] CHK002 - Is the authorization requirement for the restore action stated explicitly (FR-001 only covers upload), or is "same as upload" an assumption left implicit? [Gap, FR-001/FR-006] — **Resolved**: same FR-001 edit as CHK001.
- [ ] CHK003 - Does the design specify a maximum number of retained versions per SSP, or explicitly state that retention is unbounded by design? [Completeness, Consequences section]
- [ ] CHK004 - Are requirements defined for what the SSP page shows when the current image fails to decode/render client-side (broken image state)? [Gap, Edge Cases]
- [x] CHK005 - Is there a requirement covering image pixel dimensions (width/height), or only file size — i.e. is a small-file/huge-dimension "decompression bomb" upload explicitly in or out of scope? [Gap] — **Resolved**: Task 14 now adds an explicit pixel-dimension cap alongside the file-size cap and Pillow's built-in decompression-bomb guard.
- [ ] CHK006 - Are requirements defined for sanitizing/limiting `original_filename` before it is stored and later rendered in the history list? [Gap, Security]

## Clarity

- [ ] CHK007 - Is the "5 MB" size cap in FR-002 quantified precisely (e.g. 5 × 1024 × 1024 bytes vs 5,000,000 bytes) so two implementers would enforce the identical limit? [Clarity, FR-002]
- [ ] CHK008 - Is "near the other overview fields" in FR-005 specific enough to be implemented consistently (exact position relative to authorization boundary / FIPS ratings), or does it leave layout to interpretation? [Clarity, FR-005]
- [ ] CHK009 - Does FR-002's "verify the upload is a decodable PNG or JPEG image" specify what "decodable" means precisely enough to test (e.g. must open and verify without exception via a named library/method)? [Clarity, FR-002]

## Consistency

- [ ] CHK010 - Is the permission model in FR-001 ("no new role... matches `ssp.edit`") consistent with how User Story 1's acceptance scenarios describe access, with no contradicting statement elsewhere in the section? [Consistency]
- [ ] CHK011 - Does the "append-only, never edited or deleted" rule in FR-004/FR-006 stay consistent with the Edge Cases entry about restoring the already-current version (which allows creating a duplicate rather than special-casing it)? [Consistency]
- [ ] CHK012 - Is the audit-logging requirement (FR-007) consistent in scope with the ADR feature's audit requirement (FR-012 in the first section) — same `log_event()` pattern, comparable level of detail? [Consistency, cross-feature]

## Measurability

- [ ] CHK013 - Can SC-002 ("100% of non-image or oversized upload attempts are rejected before anything is written") be verified without ambiguity about what counts as "written" (e.g. does a rejected form re-render still touch the DB in any partial way)? [Measurability, SC-002]
- [ ] CHK014 - Is SC-003's "immediately shows the restored image as current" measurable without a defined time bound, or is "immediately" understood to mean "on the redirect response following the restore POST"? [Measurability, SC-003]
- [ ] CHK015 - Does FR-008 (cascade delete) have a corresponding measurable success criterion, or does it rely solely on the Edge Cases note? [Measurability, FR-008]

## Coverage

- [ ] CHK016 - Are requirements defined for the case where the same image bytes are uploaded twice in a row (duplicate content) — is dedup expected, or is a new version always created regardless? [Coverage, Edge Cases]
- [x] CHK017 - Are requirements defined for concurrent uploads to the same SSP (two requests computing `version_number` at once) — is a race condition explicitly accepted, or does FR-004 need a concurrency-safety clause? [Coverage, FR-004] — **Resolved**: Task 13 adds a `UniqueConstraint("ssp_id", "version_number")`, turning a silent race into a database-enforced integrity error.
- [x] CHK018 - Are the `Content-Type`/`Content-Disposition` requirements for the image-serving route specified precisely enough to rule out the served image being interpreted as something other than the declared image type by a browser? [Coverage, Security, Design Notes] — **Resolved**: Task 15 now specifies `Content-Disposition: inline` and `X-Content-Type-Options: nosniff` explicitly.
- [ ] CHK019 - Does the design state what happens to the localization requirement (FR-009) when a Pillow-level decode error message would otherwise leak library-specific text to the user? [Coverage, FR-002/FR-009]

## Summary

- **Total Items:** 19 (5 resolved via `/minispec.analyze`, 2026-08-29)
- **Focus Areas:** Completeness (6), Clarity (3), Consistency (3), Measurability (3), Coverage (4)
- **Resolved (analysis pass, 2026-08-29):**
  - CHK001/CHK002 — FR-001 in `design.md` extended to explicitly cover the restore and image-serving routes, not just upload.
  - CHK005 — Task 14 adds a pixel-dimension cap alongside the file-size cap.
  - CHK017 — Task 13 adds `UniqueConstraint("ssp_id", "version_number")` to close the concurrent-upload race.
  - CHK018 — Task 15 specifies `Content-Disposition: inline` and `X-Content-Type-Options: nosniff` on the image route.
- **Remaining open items:** CHK003, CHK004, CHK006–CHK016 (excl. CHK012, CHK015), CHK019 are lower-severity wording/scope items, left as implementation-time notes rather than blocking design.md edits (see `/minispec.analyze` report, 2026-08-29, for rationale on each).
