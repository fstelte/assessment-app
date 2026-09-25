---
type: checklist
domain: general
feature: component-tiering
created: 2026-09-25
status: completed
---

# General Requirements Quality Checklist

**Purpose:** Validate the component tiering requirements are complete, clear, and consistent.
**Feature:** component-tiering (`design.md`, decisions 20260925-0620 and 20260925-0625)

## Completeness

- [x] CHK001 - Is the behaviour defined when a `BiaTier` that components reference is deleted or its level changed (nullify, block, or cascade)? [Gap, Data Model]
- [x] CHK002 - Is it specified who may set or change a component's tier (same roles as editing the component, or restricted)? [Gap]
- [x] CHK003 - Are requirements defined for existing incident steps that already contain copied RTO/RPO text when a tier goal later changes? [Gap, Consumers]
- [x] CHK004 - Is the treatment of a tier that defines only one of RTO or RPO goal specified for the availability form and effective values? [Gap, Components/Forms]
- [x] CHK005 - Are all views that currently show a BIA tier per component (SSP, dashboard, archived list, tier export) listed as in or out of scope? [Coverage, Scope]
- [x] CHK006 - Are the audit requirements defined for tier changes on a component (fields, action names)? [Completeness, Consumers]

## Clarity

- [x] CHK007 - Is "largest unit that divides the value evenly" defined for edge values (0 s, values above 1 day, non-integer results)? [Clarity, Decision 0625]
- [x] CHK008 - Are the unit labels (s, min, h, d) specified per locale (en and nl)? [Clarity, Gap]
- [x] CHK009 - Is "applied directly" clarified as read-only display versus a stored copy? [Clarity, Overview]
- [x] CHK010 - Is the read-only wording in the availability form ("From TIER x: 4 h") specified exactly, including the case where it is inherited from the BIA tier? [Clarity, Forms]
- [x] CHK011 - Is "Not set" defined consistently (same label) across component views, exports and incident prefill? [Clarity, Consistency]

## Consistency

- [x] CHK012 - Do the BIA-level tier requirements and the component-level requirements use one label format (`TIER n > name`)? [Consistency]
- [x] CHK013 - Is the Authentication Overview's shift from BIA tier to effective tier reconciled with decision 20260918-0552 (tier/info-type summary), which that decision's scope boundary describes differently? [Consistency, Consumers]
- [x] CHK014 - Do the export requirements (stored RTO/RPO text) align with on-screen requirements (effective values), and is the difference intentional and documented? [Consistency, Decision 0625]
- [x] CHK015 - Is the "no ceiling or floor" rule consistent with any reporting that groups components under their BIA's tier? [Consistency]

## Measurability

- [x] CHK016 - Does each task have acceptance criteria that can be objectively verified against a stated requirement, including RTO/RPO fallback order? [Measurability, Tasks]
- [x] CHK017 - Is there a requirement that can be tested to show old free-text values are preserved after a tier goal applies? [Measurability, Decision 0625]

## Coverage

- [x] CHK018 - Is the import requirement defined for how a component's tier is identified in files (id, level, or label), given ids may differ between environments? [Gap, Consumers]
- [x] CHK019 - Are requirements defined for import files that reference an unknown tier or omit the column? [Edge Case, Consumers]
- [x] CHK020 - Is the behaviour defined for a component whose BIA has no tier and which has no tier of its own? [Edge Case]
- [x] CHK021 - Are migration and rollback requirements defined for existing data (no backfill, nullable) including the downgrade path? [Coverage, Migration]

## Summary

- **Total Items:** 21
- **Focus Areas:** completeness (6), clarity (5), consistency (4), measurability (2), coverage (4)
- **Key Gaps Identified:** tier deletion behaviour (CHK001), tier identification in import files (CHK018), single-goal tiers (CHK004), locale unit labels (CHK008), effect on already-copied incident steps (CHK003)
## Resolutions

All 21 items resolved in `design.md` and decision `20260925-0640-component-tiering-requirement-resolutions`; task acceptance criteria updated in `tasks.md`.

Reopened by /minispec.analyze and resolved again after correcting design.md, tasks.md and decision 20260925-0640: CHK005 and CHK014 (component views, availability summary aggregation), CHK018 and CHK019 (CSV/SQL import and export rather than JSON).
