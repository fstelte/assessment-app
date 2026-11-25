---
type: checklist
domain: general
feature: 20261119-182410-ssp-architecture-overview-multiple-files
created: 2026-11-19
status: completed
---

# General Requirements Quality Checklist

**Purpose:** Check that the multi-file architecture-overview requirements are
complete, clear, consistent and testable. The checklist weighs data integrity
(the destructive migration), upload safety and edge cases most heavily.
**Feature:** 20261119-182410-ssp-architecture-overview-multiple-files

## Completeness

- [x] CHK001 - Does the design say whether the migration's deletion of historical versions is recorded anywhere (an audit row per pruned file, a count in the migration log, or nothing)? Today every delete writes `ssp_architecture_overview_deleted`, and the migration bypasses that. [Gap, Decision 20261119-1826]
- [x] CHK002 - Is there a requirement for operators to back up the database (or export the history) before upgrading, beyond the release-notes warning? The data loss cannot be undone. [Gap, Design §Constitution Compliance]
- [x] CHK003 - Does the design define the tie-break order for files uploaded in one batch? They share almost the same `uploaded_at`. Is the order by `id` (insertion), and does insertion follow the browser's selection order? [Gap, Decision 20261119-1828]
- [x] CHK004 - Is it specified which filename appears in per-file error messages: the raw browser filename (the user recognises it) or the cleaned `_safe_upload_filename` value (what gets stored)? [Gap, Decision 20261119-1827]
- [x] CHK005 - Are the exact new and changed translation keys and their English/Dutch wording listed? Includes the plural label, count-aware flash, `file_prefix`, `image_alt` and `delete.confirm(filename)`. [Completeness, Design §i18n]
- [x] CHK006 - Does the design say whether the upload flash names the uploaded files or only gives a count? [Gap, Design §Routes]

## Clarity

- [x] CHK007 - Is "no count limit" reconciled with Werkzeug 3.1's default `max_form_parts = 1000`? That limit rejects very large batches with a 413 and no friendly message. Is that acceptable, or should the 413 get its own error page? [Clarity, Decision 20261119-1827]
- [x] CHK008 - Is "all or nothing" defined for **server-side** failures too (for example a DB error at commit after some rows were flushed), not just validation failures? [Clarity, Decision 20261119-1827]
- [x] CHK009 - Is "empty part" defined precisely: `filename == ""` only, or also a zero-byte file with a name? Does a zero-byte file give `required`, `invalid_image` or `invalid_pdf`? [Clarity, Design §Edge Cases]
- [x] CHK010 - Is the open question about renaming the relationship and table to `*_files` settled with an explicit criterion, rather than "only if trivial"? [Clarity, Design §Open Questions]
- [x] CHK011 - Is the downgrade behaviour stated precisely for rows uploaded after the upgrade (several per SSP)? Do they all survive the downgrade, with the newest becoming "current"? [Clarity, Decision 20261119-1826]

## Consistency

- [x] CHK012 - Is the design's temporary `desc` ordering (tasks.md Task 2) consistent with the design document, which only mentions `asc`? [Consistency, Design §Model vs Tasks §Task 2]
- [x] CHK013 - Do the audit `details` match between upload (`ssp_id`, `original_filename`) and delete (`ssp_id`, `original_filename`)? Is the change to the audit event shape noted for anyone who reads these events? [Consistency, Design §Routes]
- [x] CHK014 - Is the existing form-field name `image` → `files` rename reflected in every place that names it (template `hidden_tag`, help `aria-describedby`, error loop, tests)? [Consistency, Tasks §Task 4]
- [x] CHK015 - Are the parts of decision `20261118-1505` that are superseded and the parts that remain (types, limits, PDF as attachment, help text) listed in one place, so they don't contradict each other? [Consistency, Decision 20261119-1825]

## Measurability

- [x] CHK016 - Are acceptance criteria for the migration stated with concrete fixture data (for example "SSP A with versions 1, 2, 3 and SSP B with 1 → rows A:3 and B:1 remain")? [Measurability, Tasks §Task 2]
- [x] CHK017 - Is the manual browser check for the stacked layout defined with specific scenarios (one image, one PDF, mixed, narrow viewport, both themes)? [Measurability, Tasks §Task 3]

## Coverage

- [x] CHK018 - Is page-weight behaviour addressed when an SSP has many large images? For example, is `loading="lazy"` on each `<img>` required or excluded? [Coverage, Decision 20261119-1828]
- [x] CHK019 - Is server memory use addressed for a large batch? Up to N × 10 MB is held in memory before the single commit. Is this accepted explicitly alongside the request-size risk? [Coverage, Decision 20261119-1827]
- [x] CHK020 - Is double submission addressed (a double-click or re-POST creating duplicate rows), or explicitly accepted given that duplicate filenames are allowed? [Coverage, Design §Edge Cases]
- [x] CHK021 - Is the mobile layout of the per-file header row specified (long filenames truncating, delete button placement), in line with the existing PDF card's `sm:` breakpoints? [Coverage, Decision 20261119-1828]
- [x] CHK022 - Is it confirmed that no other consumer reads `version_number` or `architecture_overview_versions[0]` (SSP exports, reports, API, admin backup/restore)? If there are none, does the design say so? [Coverage, Design §Components]
- [x] CHK023 - Is it stated that upload and delete permissions stay "any logged-in user", and that this is accepted, given that one user can now delete any file in the set? [Coverage, Design §Constitution Compliance]

## Summary

- **Total Items:** 23
- **Focus Areas:** migration data loss and audit (CHK001, 002, 011, 016); batch upload semantics (CHK004, 007, 008, 009, 019, 020); ordering and naming consistency (CHK003, 012, 014); UX and coverage (CHK018, 021, 022)
- **Key Gaps Identified:**
  - The migration deletes history without audit rows or a backup step (CHK001, CHK002).
  - The Werkzeug `max_form_parts` limit silently contradicts "no count limit" (CHK007).
  - Design and tasks disagree on the interim sort order (CHK012).
  - The batch tie-break order and which filename shows in errors are not defined (CHK003, CHK004).

## Resolution

All 23 items were resolved on 2026-11-20 in decision
`20261120-0900-architecture-overview-multi-file-checklist-gap-resolutions`,
and design.md and tasks.md were updated to match. While working on CHK007, an
extra gap came up: the bundled nginx `client_max_body_size 12m` capped every
batch at about 12 MB. The resolution raises it to `100m` and adds a browser
check (the user decided this; new Task 5).
