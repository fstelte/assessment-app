---
type: checklist
domain: general
feature: 20261118-074624-risk-workspace-sync-bia-filter
created: 2026-11-18
status: completed
---

# General Requirements Quality Checklist

**Purpose:** Check that the requirements for targeted component sync, the
actual (residual) score and the BIA filter are complete, clear and consistent.
**Feature:** 20261118-074624-risk-workspace-sync-bia-filter

## Completeness

- [x] CHK001 - Does the design say how the admin risk register (`/admin/risks`, `/admin/risks/<id>`, which computes `risk.score()` in `admin/routes.py`) shows the score: actual or initial? Today it labels the value `inherent_risk_score`. [Gap, Design §5]
  - ✅ Resolved: the admin list and edit pages use the actual score (Design §8, Task 8).
- [x] CHK002 - Does the design say whether the SSP risk severity summary (`ssp/routes.py`, which uses `risk.determine_severity()` and skips closed risks) uses actual severity? Mitigated risks will no longer be closed, so with the initial score they would inflate that summary. [Gap, Consistency]
  - ✅ Resolved: the SSP summary uses actual severity, and closed risks are still excluded (Design §8, Task 8).
- [x] CHK003 - Is there a requirement for whether sync-driven changes (components replaced, `mitigated_at` set or cleared, risk reopened) are written to the audit log? Constitution II asks for audit visibility on sync changes. [Gap, Design §3]
  - ✅ Resolved: one `risk_synced_from_threat` event per risk, only when something changed, plus `risk_created_from_threat` (Design §3, Task 3).
- [x] CHK004 - Are requirements defined for how a *manual* risk shows residual values that are filled in while "Mitigated" is unchecked: ignored, shown as a hint, or rejected? [Completeness, Design §4]
  - ✅ Resolved: residual values are stored but don't affect the score, and the card shows nothing extra (Design §4).
- [x] CHK005 - Does the design state what the *API* does with `mitigated: true` when `mitigated_at` is already set (keep the timestamp, as the form does)? Is an omitted field distinguished from an explicit `null` for the residual fields? [Completeness, Design §7]
  - ✅ Resolved: `mitigated: true` keeps the timestamp, an omitted field is unchanged, `null` clears it (Design §7, Task 6).
- [x] CHK006 - Are the translation keys and the EN and NL copy listed for the new labels: Mitigated pill, "Initial → Residual" line, "residual not set", the filter label, Apply and Clear? [Completeness, Constitution IV]
  - ✅ Resolved: Tasks 4, 5 and 7 add the EN and NL keys, and Task 9 checks they match.
- [x] CHK007 - Does the design say whether the matrix footnote and heading ("Plot every recorded risk…", "Scores reflect the configured impact and chance weights…") change to say they show the actual score? [Gap, Design §5]
  - ✅ Resolved: the heading and footnote say they show the actual score (Design §5, Task 5).

## Clarity

- [x] CHK008 - Is the asset → component name match defined precisely: case sensitivity, trimming whitespace, and what happens when a BIA has two components with the same name? [Clarity, Decision 0750]
  - ✅ Resolved: case-insensitive, whitespace trimmed, all same-named components linked and deduplicated (Design §1, Task 1).
- [x] CHK009 - Is it specified whether only `AssetType.COMPONENT` assets are matched, or every asset type (data flow, data store, …)? [Clarity, Design §1]
  - ✅ Resolved: any AssetType is matched (Design §1).
- [x] CHK010 - Is the "treatment == MITIGATE" gate defined for mitigated scenarios? Status Mitigated with treatment Accept or Transfer still closes the risk, so is that intended? [Clarity, Design §3]
  - ✅ Resolved: the treatment gate stays, so Mitigated with another treatment closes the risk (Design §3, Task 3).
- [x] CHK011 - Is "Out of scope: CSV/PDF exports of the risk workspace, *if any*" resolved to a definite statement (none exist, or name them and say how they're handled)? [Clarity, Design §Out of Scope]
  - ✅ Resolved: the risk module has no exports (Design §Out of Scope).
- [x] CHK012 - Is the hero metric "mitigate" (count of treatment = mitigate) clearly told apart from the new "Mitigated" state in the labels, so users don't confuse the two? [Clarity, Design §5]
  - ✅ Resolved: the metric is relabelled "Treatment: mitigate" (Design §5, Task 5).

## Consistency

- [x] CHK013 - Do the design and Decision 0751 agree on the rule for "mitigated with no residual values" (fall back to initial, plus a muted hint) in every surface: card, matrix, edit page, API `actual_score`? [Consistency]
  - ✅ Resolved: "Fall back to initial, plus a hint" applies to the card, matrix, edit page and API (Decision 0751/0802/0830).
- [x] CHK014 - Is the precedence defined when a risk has both `closed_at` and `mitigated_at` set (for example a manual risk closed after being mitigated): which pill, which score, and is it in the matrix? [Consistency, Edge Case]
  - ✅ Resolved: both pills are shown with the actual score, and closed risks stay in the matrix (Design §5).
- [x] CHK015 - Are PASTA-published risks (`publish_pasta_conclusion_to_risk`) handled consistently? They show the new form fields, but republishing never touches `mitigated_at` or residual values, so is a manual mitigated flag on them kept? [Consistency, Design §Out of Scope]
  - ✅ Resolved: republishing leaves the mitigated and residual fields alone, and PASTA risks stay editable (Design §4).
- [x] CHK016 - Does the "scenario is the source of truth" rule for linked risks (edit GET overwrites) match showing editable Mitigated and residual fields on the form, or must the design resolve the open question first? [Consistency, Design §Open Questions]
  - ✅ Resolved: synced fields are read-only for linked risks and posted values are ignored (Design §4, Task 4).

## Measurability

- [x] CHK017 - Does every acceptance criterion in tasks.md name concrete inputs and expected outputs (for example 4×4 → residual 2×3 shows 6), rather than "works"? [Measurability, tasks.md]
  - ✅ Resolved: every task has concrete acceptance criteria, including the new Task 8.
- [x] CHK018 - Is the "components impacted" metric defined under a BIA filter: count every component of the matching risks, or only those in the selected BIAs? [Measurability, Design §6]
  - ✅ Resolved: under a filter, only components in the selected BIAs are counted (Design §6, Task 7).
- [x] CHK019 - Is the residual-vs-initial relationship defined? May a residual score exceed the initial score, and if not, is that a validation error or a warning? [Measurability, Edge Case]
  - ✅ Resolved: residual higher than initial is allowed, with no validation (Design §4).

## Coverage

- [x] CHK020 - Are migration and rollout effects described for operators: existing synced risks lose fallback components, archived risks of mitigated scenarios reopen, downgrade drops residual data? Is there a release-notes requirement (Constitution V)? [Coverage]
  - ✅ Resolved: the release-notes requirement is in Design §Rollout and Task 9.
- [x] CHK021 - Is the case of a scenario whose threat model has no BIA (`context_scope_id` NULL), or whose BIA was deleted, covered by sync and display (risk with no components, invisible under any BIA filter)? [Coverage, Edge Case]
  - ✅ Resolved: no BIA means no components, so the risk matches no filter (Design §1, §6).
- [x] CHK022 - Are BIA filter requirements defined for archived risks (shown or hidden when a filter is active) and for the BIA option list (all BIAs with components, or only those with linked risks)? [Coverage, Design §Open Questions]
  - ✅ Resolved: archived risks are shown, and the options are BIAs with at least one component (Design §6).
- [x] CHK023 - Are authorization requirements for the BIA filter stated? Should every authenticated user see every BIA name in the dropdown, matching today's dashboard, or is it scoped? [Coverage, Constitution II]
  - ✅ Resolved: access is unchanged, so any authenticated user sees all BIA options (Design §6).
- [x] CHK024 - Is behaviour defined for a scenario that moves from Mitigated back to an open status and later to Mitigated again: is `mitigated_at` a new timestamp or the original one? [Coverage, Decision 0800]
  - ✅ Resolved: re-mitigation gets a new timestamp (Design §3, Task 3).

## Summary

- **Total Items:** 24
- **Focus Areas:** sync semantics (8), score consistency across surfaces (7), UX copy and labels (4), filter behaviour (3), audit, rollout and auth (2)
- **Status:** All 24 items resolved on 2026-11-18. See decision `20261118-0830-risk-residual-checklist-gap-resolutions`.
- **Key Gaps Identified (now resolved):**
  - The admin risk register and the SSP severity summary use the initial score and are not covered by the design (CHK001, CHK002). Once mitigated risks stop being closed, the SSP summary will over-report.
  - There is no audit requirement for sync-driven changes (CHK003).
  - The name-matching rules and the asset-type scope are undefined (CHK008, CHK009).
  - Mitigated plus a non-MITIGATE treatment still closes the risk, which may conflict with the user's intent (CHK010).
