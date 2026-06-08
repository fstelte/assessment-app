# Tasks: PASTA Threat Modeling

**Input**: Design documents from `/specs/003-pasta-threat-modeling/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Include test tasks whenever the feature changes behavior, security, data flow, or schema. Omit them only when the work is strictly documentation or non-executable project metadata.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the threat module for model-level PASTA work and reserve the shared implementation surfaces.

- [X] T001 Add canonical PASTA workflow constants and shared status definitions in scaffold/apps/threat/models.py and scaffold/apps/threat/services.py
- [X] T002 [P] Add baseline PASTA route and template entry points in scaffold/apps/threat/routes.py and scaffold/apps/threat/templates/threat/model_detail.html
- [X] T003 [P] Add baseline PASTA translation keys in scaffold/translations/en.json and scaffold/translations/nl.json

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core schema and shared workflow infrastructure that MUST be complete before ANY user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Decide and document compatibility handling for existing per-scenario PASTA fields in scaffold/apps/threat/models.py, specs/003-pasta-threat-modeling/plan.md, and migrations/versions/
- [X] T005 Create the Alembic migration for model-level PASTA workflow tables and threat model metadata in migrations/versions/
- [X] T006 Implement ThreatModel extensions plus PastaStageRecord, PastaFinding, and link models in scaffold/apps/threat/models.py
- [X] T007 [P] Implement stage initialization, unlock, and revalidation helpers in scaffold/apps/threat/services.py
- [X] T008 [P] Extend threat model creation/edit forms for methodology and bootstrap source handling in scaffold/apps/threat/forms.py and scaffold/apps/threat/templates/threat/model_form.html
- [X] T009 Implement shared PASTA-aware model detail routing and methodology branching in scaffold/apps/threat/routes.py and scaffold/apps/threat/templates/threat/model_detail.html
- [X] T010 Add foundational schema and model initialization coverage in tests/test_threat_pasta_models.py

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Run a PASTA threat model through all seven stages (Priority: P1) 🎯 MVP

**Goal**: Deliver a complete model-level PASTA workflow with ordered stages, light gating, resumable progress, and explicit revalidation.

**Independent Test**: Create a new PASTA threat model, progress through all seven stages with saved summaries and findings, reopen it later, and verify stage unlocks, saved state, and revalidation behavior all work without relying on STRIDE-LM reuse or downstream scenario generation.

### Tests for User Story 1 ⚠️

- [X] T011 [P] [US1] Add create/progress/reopen workflow tests in tests/test_threat_pasta_routes.py
- [X] T012 [P] [US1] Add stage gating and revalidation tests in tests/test_threat_pasta_workflow.py
- [X] T013 [P] [US1] Add authorization and audit regression tests for PASTA model creation, stage editing, and revalidation in tests/test_threat_pasta_routes.py

### Implementation for User Story 1

- [X] T014 [US1] Implement PASTA model creation and initial stage-record setup in scaffold/apps/threat/routes.py and scaffold/apps/threat/services.py
- [X] T015 [US1] Implement stage edit and stage summary forms in scaffold/apps/threat/forms.py and scaffold/apps/threat/templates/threat/pasta_stage_form.html
- [X] T016 [US1] Implement core PASTA finding create, edit, save, and review behavior in scaffold/apps/threat/routes.py, scaffold/apps/threat/forms.py, and scaffold/apps/threat/models.py
- [X] T017 [US1] Implement ordered stage review panels and workflow status display in scaffold/apps/threat/templates/threat/model_detail.html and scaffold/apps/threat/templates/threat/pasta_stage_panel.html
- [X] T018 [US1] Persist stage completion notes, reopen behavior, and revalidation markers in scaffold/apps/threat/routes.py and scaffold/apps/threat/models.py
- [X] T019 [US1] Update workflow and revalidation copy in scaffold/translations/en.json and scaffold/translations/nl.json

**Checkpoint**: At this point, User Story 1 should be fully functional and independently testable.

---

## Phase 4: User Story 2 - Reuse STRIDE-LM where it strengthens PASTA analysis (Priority: P2)

**Goal**: Reuse existing threat-model context through one-way bootstrap and optional finding-level STRIDE-LM mappings without forcing STRIDE semantics onto all PASTA findings.

**Independent Test**: Bootstrap a new PASTA model from an existing STRIDE-LM model, add findings with and without STRIDE-LM mappings, and confirm reused context and mappings persist without blocking non-mapped findings.

### Tests for User Story 2 ⚠️

- [X] T020 [P] [US2] Add bootstrap conversion tests in tests/test_threat_pasta_bootstrap.py
- [X] T021 [P] [US2] Add finding-level STRIDE-LM mapping and context reuse tests in tests/test_threat_pasta_mappings.py

### Implementation for User Story 2

- [X] T022 [US2] Implement one-way STRIDE-LM-to-PASTA bootstrap service and route in scaffold/apps/threat/services.py and scaffold/apps/threat/routes.py
- [X] T023 [US2] Implement finding asset links, library-entry links, and STRIDE-LM mapping persistence in scaffold/apps/threat/models.py and scaffold/apps/threat/routes.py
- [X] T024 [US2] Add bootstrap actions and finding mapping controls to scaffold/apps/threat/templates/threat/model_detail.html and scaffold/apps/threat/templates/threat/pasta_stage_form.html
- [X] T025 [US2] Add bootstrap and mapping audit/localization updates in scaffold/apps/threat/routes.py, scaffold/translations/en.json, and scaffold/translations/nl.json

**Checkpoint**: At this point, User Stories 1 and 2 should both work independently.

---

## Phase 5: User Story 3 - Review PASTA results as actionable business risk output (Priority: P3)

**Goal**: Make PASTA results reviewable in the interactive UI and existing export surfaces, and allow selected findings to generate or link standard downstream threat scenarios with traceability.

**Independent Test**: Review a completed PASTA model in the UI, export it as HTML/PDF/CSV, and generate or link a downstream threat scenario from a selected finding while preserving traceability to the source PASTA analysis.

### Tests for User Story 3 ⚠️

- [X] T026 [P] [US3] Add methodology-aware HTML/PDF/CSV export permission and rendering tests in tests/test_threat_pasta_exports.py
- [X] T027 [P] [US3] Add downstream scenario generation, linking, and audit-event tests in tests/test_threat_pasta_scenarios.py

### Implementation for User Story 3

- [X] T028 [US3] Implement downstream scenario generation and link routes for selected PASTA findings in scaffold/apps/threat/routes.py and scaffold/apps/threat/services.py
- [X] T029 [US3] Implement PASTA export projection and CSV branching logic in scaffold/apps/threat/services.py and scaffold/apps/threat/routes.py
- [X] T030 [US3] Update methodology-aware HTML/PDF export rendering in scaffold/apps/threat/templates/threat/export_report.html and scaffold/apps/threat/templates/threat/pasta_review_summary.html
- [X] T031 [US3] Surface linked/generated scenario traceability in scaffold/apps/threat/templates/threat/model_detail.html and scaffold/apps/threat/templates/threat/scenario_detail.html
- [X] T032 [US3] Update export and review terminology in scaffold/translations/en.json and scaffold/translations/nl.json

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish migration compatibility, documentation, and end-to-end validation across all stories.

- [X] T033 [P] Update release-facing threat model documentation in docs/models.md and docs/history.md
- [X] T034 [P] Update operator guidance for PASTA versus STRIDE-LM bootstrap in README.md and docs/history.md
- [X] T035 Run the quickstart validation flow against specs/003-pasta-threat-modeling/quickstart.md and capture any task-driven fixes in tests/test_threat_routes.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - blocks all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational completion.
- **Polish (Phase 6)**: Depends on the user stories selected for release.

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Foundational and delivers the MVP PASTA workflow.
- **User Story 2 (P2)**: Starts after Foundational and reuses the PASTA workflow foundation without requiring User Story 3.
- **User Story 3 (P3)**: Starts after Foundational and can be completed after User Story 1 if the release only needs review/export and downstream operationalization.

### Within Each User Story

- Tests for behavior and schema changes must be written or updated before implementation is considered complete.
- Models and persistence rules come before route wiring.
- Services come before template integration.
- UI/export integration comes after core persistence and route behavior.

### Parallel Opportunities

- T002 and T003 can run in parallel after T001.
- T007 and T008 can run in parallel after T006.
- T011, T012, and T013 can run in parallel within User Story 1.
- T020 and T021 can run in parallel within User Story 2.
- T026 and T027 can run in parallel within User Story 3.
- T033 and T034 can run in parallel during Polish.

---

## Parallel Example: User Story 1

```bash
# Launch User Story 1 tests together:
Task: "Add create/progress/reopen workflow tests in tests/test_threat_pasta_routes.py"
Task: "Add stage gating and revalidation tests in tests/test_threat_pasta_workflow.py"
```

## Parallel Example: User Story 2

```bash
# Launch User Story 2 tests together:
Task: "Add bootstrap conversion tests in tests/test_threat_pasta_bootstrap.py"
Task: "Add finding-level STRIDE-LM mapping and context reuse tests in tests/test_threat_pasta_mappings.py"
```

## Parallel Example: User Story 3

```bash
# Launch User Story 3 tests together:
Task: "Add methodology-aware HTML/PDF/CSV export permission and rendering tests in tests/test_threat_pasta_exports.py"
Task: "Add downstream scenario generation, linking, and audit-event tests in tests/test_threat_pasta_scenarios.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1.
4. Validate the full seven-stage PASTA workflow independently before expanding scope.

### Incremental Delivery

1. Finish Setup and Foundational work to establish the model-level PASTA infrastructure.
2. Deliver User Story 1 as the MVP workflow.
3. Add User Story 2 for STRIDE-LM reuse and bootstrap.
4. Add User Story 3 for export/review completeness and downstream operationalization.
5. Finish with Polish tasks for migration compatibility, docs, and quickstart validation.

### Parallel Team Strategy

1. One developer handles schema and shared services while another prepares form/template scaffolding during Foundational.
2. After Foundational, one developer can own User Story 1 while another prepares User Story 2 or User Story 3 tests.
3. Merge User Story 2 and User Story 3 carefully because both touch scaffold/apps/threat/routes.py and scaffold/apps/threat/templates/threat/model_detail.html.

---

## Notes

- [P] tasks indicate file-independent work that can run in parallel after their prerequisites.
- Each user story is independently testable, but shared file conflicts in the threat module still need coordination.
- The release-critical migration task must preserve existing STRIDE-LM-only models without forced conversion.
- Keep audit, translation, and export updates in scope as first-class implementation work rather than end-of-cycle cleanup.
