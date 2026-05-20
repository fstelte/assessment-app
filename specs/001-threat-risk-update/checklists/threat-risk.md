# Threat-Risk Checklist: Threat Model and Risk Updates

**Purpose**: Validate the completeness, clarity, consistency, and review-readiness of the combined threat multi-select and risk ticket-link requirements
**Created**: 2026-05-20
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are requirements explicit that multi-select asset assignment applies to both create and edit flows for threat scenarios? [Completeness, Spec §User Story 1, Spec §FR-001]
- [x] CHK002 Do requirements define whether at least one asset and at least one STRIDE-LM category are mandatory for STRIDE scenarios? [Gap, Spec §FR-001, Spec §FR-002]
- [x] CHK003 Are requirements explicit about how non-STRIDE methodologies remain supported while multi-category selection applies to STRIDE-LM? [Completeness, Spec §Clarifications, Spec §Assumptions]
- [x] CHK004 Do requirements define whether risk ticket links are optional, conditionally required, or expected for all risk treatments? [Clarity, Spec §User Story 4, Spec §FR-010]

## Requirement Clarity

- [x] CHK005 Is “the same asset selections remain associated” precise enough to say whether order matters or only membership matters? [Ambiguity, Spec §User Story 1]
- [x] CHK006 Are the rules for “invalid, duplicate, or no-longer-available selections” specific enough to distinguish validation failures from preserved historical associations? [Clarity, Spec §FR-006, Spec §Edge Cases]
- [x] CHK007 Is “short label” for each risk ticket link quantified with a concrete length or formatting rule? [Clarity, Spec §FR-011]
- [x] CHK008 Is “displayed consistently” defined for every required surface, including form re-open, detail view, summary view, CSV export, HTML/PDF export, dashboard, and API output? [Clarity, Spec §User Story 2, Spec §User Story 3, Spec §User Story 4]

## Requirement Consistency

- [ ] CHK009 Do the requirements stay consistent about scope, avoiding accidental expansion into broader threat-risk synchronization beyond multi-selects and ticket links? [Consistency, Spec §Assumptions, Spec §User Stories]
- [x] CHK010 Are compatibility expectations consistent between the spec and the plan for existing single-value records and deprecated single-value aliases? [Consistency, Spec §FR-004, Spec §Security, Audit, and Operations, Gap]
- [x] CHK011 Are the STRIDE-LM category requirements consistent with the continued support for PASTA, LINDDUN, and OWASP scenarios? [Consistency, Spec §Clarifications, Spec §Assumptions]

## Acceptance Criteria Quality

- [ ] CHK012 Can SC-001 be objectively verified without defining what counts as a duplicate scenario versus one correctly multi-assigned scenario? [Measurability, Spec §SC-001]
- [ ] CHK013 Does SC-002 define which exact summary views must satisfy the 30-second review target? [Clarity, Spec §SC-002]
- [ ] CHK014 Are success criteria defined for the risk ticket-link behavior with the same level of measurability as the threat multi-select behavior? [Coverage, Spec §SC-005]

## Scenario Coverage

- [x] CHK015 Are requirements defined for editing pre-existing single-assignment threat scenarios without forcing immediate reclassification? [Coverage, Spec §FR-004, Spec §Edge Cases]
- [ ] CHK016 Are requirements defined for reviewing scenarios with multiple assets and multiple STRIDE-LM categories in both interactive views and exports? [Coverage, Spec §User Story 3, Spec §FR-009]
- [x] CHK017 Are requirements defined for risks with zero, one, and many ticket links across create, edit, reopen, and later review flows? [Coverage, Spec §User Story 4, Spec §FR-010, Spec §FR-012]

## Edge Case Coverage

- [x] CHK018 Do requirements define what happens when an associated asset is archived or deleted after the scenario is saved? [Edge Case, Spec §Edge Cases]
- [x] CHK019 Do requirements define whether historical STRIDE-LM category assignments remain visible when category availability rules change? [Edge Case, Spec §Edge Cases]
- [x] CHK020 Do requirements define fallback behavior when one saved ticket link is malformed, unreachable, or points to a removed ticket? [Edge Case, Spec §Edge Cases]

## Non-Functional Requirements

- [x] CHK021 Are authorization requirements specific about which roles may edit versus only review multi-assignments and ticket links? [Security, Spec §FR-008, Spec §Authorization Impact]
- [x] CHK022 Are audit requirements specific enough to determine whether individual asset/category/ticket-link additions and removals must be logged separately? [Auditability, Spec §FR-007, Spec §Audit/Event Impact]
- [ ] CHK023 Are localization requirements defined for new form labels, validation messages, summary text, and export terminology across both modules? [Non-Functional, Spec §Localization Impact]

## Dependencies & Assumptions

- [x] CHK024 Are migration/backfill, API compatibility aliases, and export compatibility expectations stated as requirements rather than left as implementation assumptions? [Dependency, Spec §Migration/Backfill Impact, Spec §FR-004]
- [ ] CHK025 Is the assumption that risk ticket links belong in the same feature reconciled with any delivery sequencing or phased rollout expectations? [Assumption, Spec §Clarifications, Spec §Assumptions]

## Ambiguities & Conflicts

- [ ] CHK026 Is there a defined conflict-resolution rule if threat scenario assignments and risk ticket links are edited concurrently by different users? [Gap, Spec §Edge Cases]
- [ ] CHK027 Do the requirements clarify whether one scenario should appear in multiple category groupings in dashboards and exports, or whether a primary category still exists for reporting? [Ambiguity, Spec §User Story 2, Spec §User Story 3]

## Notes

- Audience: Reviewer during PR/spec review
- Depth: Standard
- Focus: Combined threat multi-select and risk ticket-link requirements