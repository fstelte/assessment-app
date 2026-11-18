---
type: checklist
domain: general
feature: 20261118-144354-ssp-metadata-interconnections-adr
created: 2026-11-18
status: completed
---

# General Requirements Quality Checklist

**Purpose:** Check that the SSP usability-pass requirements are complete, clear,
consistent and testable. The checklist weighs security, data integrity and edge
cases most heavily.
**Feature:** 20261118-144354-ssp-metadata-interconnections-adr

## Completeness

- [x] CHK001 - Does the design define what happens when an ADR is deleted whose predecessor was superseded from a status other than `accepted`? Today `configure_adr_form` allows superseding proposed, rejected or deprecated ADRs, so "restore to `accepted`" can be wrong, and the earlier status is not stored. [Gap, Decision 20261118-1515]
- [x] CHK002 - Does the reconcile requirement define what happens when a BIA interface name matches an existing **manual** row? Options: adopt it as `bia`, leave it manual, or add a duplicate. [Gap, Design §2]
- [x] CHK003 - Is it specified what happens when a user deletes a `bia` interconnection that is still listed in the BIA? The next view would add it again. Should delete be blocked, or explained? [Gap, Decision 20261118-1455]
- [x] CHK004 - Does the normalisation rule define whitespace collapsing and duplicate names inside the BIA `interfaces` text, beyond "trimmed, case-insensitive"? [Completeness, Design §2]
- [x] CHK005 - Are requirements defined for how `sort_order` is set and edited on the admin options page, or is the order alphabetical? [Gap, Design §3]
- [x] CHK006 - Is it specified whether option-name uniqueness per kind is case-insensitive, and what the admin sees on a duplicate? [Completeness, Decision 20261118-1500]
- [x] CHK007 - Does the migration requirement define how frequency values that differ only in case or whitespace ("Monthly" vs "monthly ") are de-duplicated when seeding options? [Completeness, Data Model]
- [x] CHK008 - Is the behaviour defined when an upload exceeds a request-size limit set before WTForms runs (`MAX_CONTENT_LENGTH` or the reverse proxy's `client_max_body_size`)? Is the 10 MB limit aligned with those settings and with `docs/deployment.md`? [Gap, Decision 20261118-1505]
- [x] CHK009 - Are audit requirements defined for interconnection rows added automatically by reconcile, and for changes to an SSP's law/frequency selection (contents of `ssp_updated` details)? [Gap, Constitution II]

## Clarity

- [x] CHK010 - Is the version-number rule unambiguous? Decision 20261118-1505 says both "version numbers are never reused" and "may reuse a deleted top number". [Clarity, Conflict]
- [x] CHK011 - Is "opens when any of these fields has a value" defined for milestones? Does an item with milestones but empty detail fields open the block? [Clarity, Decision 20261118-1510]
- [x] CHK012 - Is the exact EN/NL wording given (or delegated, with a review owner) for the intros on continuous monitoring, POA&M purpose and "Security ADRs"? [Clarity, Design §7]
- [x] CHK013 - Are the distinct upload error messages (type, size, dimensions, invalid PDF) listed with their translation keys? [Clarity, Design §4]
- [x] CHK014 - Is it specified how an inactive option already linked to an SSP is marked in the edit form and on the view/print, for example with an "(inactive)" suffix? [Clarity, Decision 20261118-1500]

## Consistency

- [x] CHK015 - Is "Security ADRs" applied the same way everywhere: nav button on the SSP view, section header, ADR list title, print/PDF header and docs? [Consistency, Constitution IV]
- [x] CHK016 - Do the rules for external links (absolute http(s), max 500 characters, `rel="noopener noreferrer"`, URL text in print) apply the same way to `adr_register_url`, `ADRRecord.external_url` and `POAMItem.jira_url`? Is the shared validator named? [Consistency]
- [x] CHK017 - Is the either/or rule for ADRs (link, or context + decision) stated identically for create and edit, including removing the link from a link-only ADR? [Consistency, Design §6]
- [x] CHK018 - Do the print/PDF requirements cover every new view element: stale-interconnection badge, option names, register URL, Jira URL, link-only ADR? [Consistency, Constitution IV "exports preserve meaning"]

## Security

- [x] CHK019 - Are the roles allowed to delete architecture-overview versions and ADRs stated explicitly with the reasoning? Today it is any logged-in user, and Constitution II requires naming the affected roles and the risk. [Security, Constitution II]
- [x] CHK020 - Is the risk of serving user-uploaded PDFs `inline` from the app's origin assessed (browser PDF viewers, embedded JavaScript)? Should PDFs be served as `attachment`, or with a restrictive per-response CSP (`sandbox`)? [Security, Decision 20261118-1505]
- [x] CHK021 - Is it specified whether the Jira link may point to any host, or must match a configured Jira base URL? [Security/Clarity, Decision 20261118-1510]
- [x] CHK022 - Are CSRF protection and a confirm prompt required for every new destructive POST route (delete version, delete ADR, admin option delete/toggle)? [Coverage, Security]

## Measurability & Coverage

- [x] CHK023 - Does every user story (US1–US7) have at least one acceptance scenario? US7 (monitoring wording) currently has none. [Measurability, Design §User Stories]
- [x] CHK024 - Are backup, full restore and partial-restore requirements stated for the new `ssp_options` and `ssp_plan_laws` tables, with an owning task and evidence? [Coverage, Tasks §2, Notes]
- [x] CHK025 - Is the acceptance for the GET-time write in reconcile defined under concurrency? Two simultaneous first views must not create duplicate rows. Is a unique constraint or retry required? [Edge Case, Decision 20261118-1455]

## Summary

- **Total items:** 25
- **Focus areas:** completeness (9), clarity (5), consistency (4), security (4), measurability and coverage (3)
- **Main gaps:**
  1. CHK001: the delete rule for superseded ADRs assumes the predecessor was `accepted`
  2. CHK010: the version-number reuse statement contradicts itself
  3. CHK002/CHK003/CHK025: reconcile edge cases (a manual row with the same name, deleting a live BIA row, concurrent views)
  4. CHK020: serving user PDFs inline
  5. CHK008: upload limit vs. the server and proxy request-size limits

## Resolutions

All 25 items are resolved in decision
`20261118-1530-ssp-usability-checklist-gap-resolutions`. The affected
decisions (1455, 1500, 1505, 1510, 1515), `design.md` and `tasks.md` are
amended to match. The user decided:
- **CHK001**: store `status_before_supersede` and restore it on delete
  (fallback `accepted`).
- **CHK002/CHK003**: a matching manual row is adopted as `bia`; live `bia`
  rows cannot be deleted.
- **CHK019**: any logged-in user may delete (consistent with the SSP); the
  risk is documented.
- **CHK020**: PDFs are served as `attachment` ("Download PDF").

Additional finding from CHK008: the bundled nginx gateway had no
`client_max_body_size`, so the 1 MB default was the likely real cause of
failed architecture uploads. This is fixed in Task 6 with `12m` plus the
deployment docs.
