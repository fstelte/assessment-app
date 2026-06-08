# Tasks: Guided PASTA Risk Analysis

**Input**: Design documents from `/specs/004-guided-pasta-risk/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Include test tasks whenever the feature changes behavior, security, data flow, or schema. Omit them only when the work is strictly documentation or non-executable project metadata.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the shared threat and risk module surfaces for guided PASTA stage guidance and stage-seven publication work.

- [X] T001 Add shared guided-stage metadata, publication-state constants, and risk-conclusion helpers in scaffold/apps/threat/models.py and scaffold/apps/threat/services.py
- [X] T002 [P] Add non-functional guided PASTA stage-navigation scaffolding in scaffold/apps/threat/templates/threat/model_detail.html
- [X] T003 [P] Add baseline guided PASTA stage and scoring terminology in scaffold/translations/en.json and scaffold/translations/nl.json

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core schema and shared workflow infrastructure that MUST be complete before ANY user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Implement legacy stage-seven `risk_conclusion` compatibility rules and backfill mapping for the new structured conclusion record in scaffold/apps/threat/models.py and migrations/versions/
- [X] T005 Create the Alembic migration for structured PASTA risk-conclusion persistence, legacy backfill, and risk linkage in migrations/versions/
- [X] T006 Implement `PastaRiskConclusion` persistence and legacy finding linkage updates in scaffold/apps/threat/models.py
- [X] T007 [P] Implement shared score mapping, publish gating, and republish projection helpers in scaffold/apps/threat/services.py
- [X] T008 [P] Extend guided PASTA forms for stage-seven scoring and publication notes in scaffold/apps/threat/forms.py and scaffold/apps/threat/templates/threat/pasta_stage_form.html
- [X] T009 Implement shared stage-seven route plumbing and model-loading helpers in scaffold/apps/threat/routes.py
- [X] T010 Add foundational schema and model coverage for structured PASTA conclusions in tests/test_threat_pasta_models.py

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Complete a guided PASTA analysis from stage inputs to final risk conclusions (Priority: P1) 🎯 MVP

**Goal**: Deliver a guided PASTA experience across stages 1 through 7 so users see stage purpose, expected inputs, downstream outputs, and a structured stage-seven risk conclusion with likelihood and impact scoring.

**Independent Test**: Create a PASTA model, progress through stages 1 through 7, record a scored risk conclusion, reopen the model, and verify each stage shows purpose, expected inputs, downstream outputs, and that stage seven shows carried-forward evidence, current scores, and revalidation state without requiring risk-workspace publication.

### Tests for User Story 1 ⚠️

- [X] T011 [P] [US1] Add guided stage-navigation, stage-purpose, and stage-seven scoring route tests in tests/test_threat_pasta_routes.py
- [X] T012 [P] [US1] Add upstream carry-forward, stage guidance completeness, and revalidation tests for `risk_impact_analysis` in tests/test_threat_pasta_workflow.py
- [X] T013 [P] [US1] Add authorization and audit regression tests for stage-seven score updates in tests/test_threat_pasta_routes.py

### Implementation for User Story 1

- [X] T014 [US1] Implement guided stage purpose, expected-input, and downstream-output presentation plus stage-seven risk-conclusion create and edit persistence in scaffold/apps/threat/routes.py and scaffold/apps/threat/services.py
- [X] T015 [US1] Implement structured likelihood, impact, and overall-score handling for PASTA conclusions in scaffold/apps/threat/services.py and scaffold/apps/threat/models.py
- [X] T016 [US1] Update guided PASTA stage inputs for stages 1 through 6 and add stage-seven scoring inputs in scaffold/apps/threat/forms.py and scaffold/apps/threat/templates/threat/pasta_stage_form.html
- [X] T017 [US1] Surface stage purpose, expected inputs, downstream outputs, carried-forward evidence, blocked reasons, and score summaries in scaffold/apps/threat/templates/threat/model_detail.html and scaffold/apps/threat/templates/threat/pasta_finding_form.html
- [X] T018 [US1] Add guided stage guidance and stage-seven scoring copy in scaffold/translations/en.json and scaffold/translations/nl.json

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Score PASTA risk conclusions and publish them to the risk workspace (Priority: P2)

**Goal**: Let threat editors explicitly publish and republish eligible PASTA conclusions into the existing risk workspace while keeping PASTA as the source of truth.

**Independent Test**: Complete a scored PASTA risk conclusion, publish it to the risk workspace, republish after a source update, and verify the linked risk is refreshed rather than duplicated.

### Tests for User Story 2 ⚠️

- [X] T019 [P] [US2] Add publish and republish route coverage for PASTA conclusions in tests/test_threat_pasta_routes.py
- [X] T020 [P] [US2] Add linked risk projection and no-duplicate regression tests in tests/test_threat_pasta_workflow.py and tests/test_risk_api.py

### Implementation for User Story 2

- [X] T021 [US2] Implement PASTA publish and republish endpoints in scaffold/apps/threat/routes.py
- [X] T022 [US2] Implement risk-workspace projection, refresh, and source-of-truth linkage in scaffold/apps/threat/services.py and scaffold/apps/threat/models.py
- [X] T023 [US2] Surface publish actions and publication state in scaffold/apps/threat/templates/threat/model_detail.html and scaffold/apps/threat/templates/threat/pasta_stage_form.html
- [X] T024 [US2] Show PASTA-origin risk links in scaffold/apps/risk/routes.py and scaffold/apps/risk/templates/risk/dashboard.html
- [X] T025 [US2] Add publish and republish audit details plus user-facing messages in scaffold/apps/threat/routes.py, scaffold/translations/en.json, and scaffold/translations/nl.json

**Checkpoint**: At this point, User Stories 1 and 2 should both work independently within the guided PASTA and risk-workspace flow.

---

## Phase 5: User Story 3 - Review and export PASTA results in the same application style (Priority: P3)

**Goal**: Make guided PASTA results reviewable in the interactive UI and the existing HTML, PDF, and CSV outputs with consistent application styling and publication-state terminology.

**Independent Test**: Review a completed guided PASTA model in the interactive UI and export it as HTML, PDF, and CSV, confirming score details, publication state, and linked risk references render consistently.

### Tests for User Story 3 ⚠️

- [X] T026 [P] [US3] Add interactive review regression coverage for published, draft, and revalidation states in tests/test_threat_pasta_routes.py
- [X] T027 [P] [US3] Add HTML/PDF/CSV regression coverage for stage-seven scoring and publication fields in tests/test_threat_pasta_exports.py

### Implementation for User Story 3

- [X] T028 [US3] Extend PASTA CSV export with score and publication columns in scaffold/apps/threat/services.py and scaffold/apps/threat/routes.py
- [X] T029 [US3] Update PASTA HTML and PDF export rendering for stage-seven score and risk-link sections in scaffold/apps/threat/templates/threat/pasta_export_report.html
- [X] T030 [US3] Align interactive review styling and risk-workspace references with existing application patterns in scaffold/apps/threat/templates/threat/model_detail.html and scaffold/apps/risk/templates/risk/dashboard.html
- [X] T031 [US3] Update reporting terminology and localized publication copy in scaffold/translations/en.json and scaffold/translations/nl.json

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish documentation, migration validation, and end-to-end verification across all stories.

- [X] T032 [P] Update guided PASTA publication and reviewer guidance in docs/risk.md and docs/history.md
- [X] T033 [P] Update structured PASTA risk-conclusion reference material in docs/models.md and docs/risk.md
- [X] T034 Validate migration/backfill behavior for existing PASTA and STRIDE data in migrations/versions/ and specs/004-guided-pasta-risk/quickstart.md
- [X] T035 Run the targeted guided PASTA validation slice from specs/004-guided-pasta-risk/quickstart.md using tests/test_threat_pasta_routes.py, tests/test_threat_pasta_exports.py, tests/test_threat_pasta_workflow.py, and tests/test_threat_pasta_models.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - blocks all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational completion.
- **Polish (Phase 6)**: Depends on the user stories selected for release.

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Foundational and delivers the MVP guided stage-seven workflow.
- **User Story 2 (P2)**: Depends on User Story 1 because publish and republish operate on scored stage-seven conclusions.
- **User Story 3 (P3)**: Depends on User Story 1 for stage-seven review content and should land after User Story 2 when linked risk-workspace output is part of the release scope.

### Within Each User Story

- Tests for stage guidance, behavior, security, and schema changes must be written or updated before implementation is considered complete.
- Persistence and model changes come before route wiring.
- Services come before template and export integration.
- UI and reporting integration come after core scoring and publication behavior is stable.

### Parallel Opportunities

- T002 and T003 can run in parallel after T001.
- T007 and T008 can run in parallel after T006.
- T011, T012, and T013 can run in parallel within User Story 1.
- T019 and T020 can run in parallel within User Story 2.
- T026 and T027 can run in parallel within User Story 3.
- T032 and T033 can run in parallel during Polish.

---

## Parallel Example: User Story 1

```bash
# Launch User Story 1 tests together:
Task: "Add guided stage-seven scoring and edit-flow tests in tests/test_threat_pasta_routes.py"
Task: "Add upstream carry-forward and revalidation tests for risk_impact_analysis in tests/test_threat_pasta_workflow.py"
Task: "Add authorization and audit regression tests for stage-seven score updates in tests/test_threat_pasta_routes.py"
```

## Parallel Example: User Story 2

```bash
# Launch User Story 2 tests together:
Task: "Add publish and republish route coverage for PASTA conclusions in tests/test_threat_pasta_routes.py"
Task: "Add linked risk projection and no-duplicate regression tests in tests/test_threat_pasta_workflow.py and tests/test_risk_api.py"
```

## Parallel Example: User Story 3

```bash
# Launch User Story 3 tests together:
Task: "Add interactive review regression coverage for published, draft, and revalidation states in tests/test_threat_pasta_routes.py"
Task: "Add HTML/PDF/CSV regression coverage for stage-seven scoring and publication fields in tests/test_threat_pasta_exports.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: confirm guided stage-seven scoring works independently before adding publication.

### Incremental Delivery

1. Finish Setup and Foundational work to establish structured stage-seven persistence and shared helpers.
2. Deliver User Story 1 as the MVP guided scoring workflow.
3. Add User Story 2 for explicit publish and republish into the risk workspace.
4. Add User Story 3 for review and export completeness.
5. Finish with Polish tasks for docs, migration validation, and quickstart verification.

### Parallel Team Strategy

1. One developer owns schema and shared services while another prepares forms and template scaffolding during Foundational.
2. After Foundational, one developer can finish User Story 1 while another prepares User Story 2 or User Story 3 tests.
3. Coordinate merges carefully because User Stories 1 through 3 all touch scaffold/apps/threat/routes.py and scaffold/apps/threat/templates/threat/model_detail.html.

---

## Notes

- [P] tasks indicate file-independent work that can run in parallel after prerequisites are satisfied.
- Each user story remains traceable to the clarified spec, but User Story 2 intentionally builds on the scored conclusions delivered in User Story 1.
- Keep audit, localization, export updates, and migration validation in scope as first-class implementation work.