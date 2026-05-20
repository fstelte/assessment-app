# Tasks: Threat Model and Risk Updates

**Input**: Design documents from `/specs/001-threat-risk-update/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Include test tasks whenever the feature changes behavior, security,
data flow, or schema. Omit them only when the work is strictly documentation or
non-executable project metadata.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the implementation scaffolding and shared copy surface for the feature.

- [X] T001 Create the Alembic revision scaffold for plural threat assignments and risk ticket links in `migrations/versions/20260520_0001_threat_risk_plural_links.py`
- [X] T002 [P] Add initial translation keys for threat multi-select and risk ticket-link copy in `scaffold/translations/en.json` and `scaffold/translations/nl.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core schema and shared service changes that MUST be complete before any user story work begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T032 [P] Add regression coverage for role-aware view/edit access to threat assignment details and risk ticket links in `tests/test_threat_routes.py` and `tests/test_risk_routes.py`
- [X] T003 Implement `ThreatScenario` asset/category association tables and relationships in `scaffold/apps/threat/models.py`
- [X] T004 Implement `RiskTicketLink` and the parent `Risk.ticket_links` relationship in `scaffold/apps/risk/models.py`
- [X] T005 Implement schema creation, deterministic backfill, and downgrade handling in `migrations/versions/20260520_0001_threat_risk_plural_links.py`
- [X] T006 [P] Refactor threat service helpers and threat-to-risk sync to consume plural asset/category relationships in `scaffold/apps/threat/services.py`
- [X] T007 [P] Refactor risk payload parsing and serialization compatibility for `ticket_links` and deprecated `ticket_url` in `scaffold/apps/risk/services.py`
- [X] T033 Enforce role-aware access checks for threat assignment and risk ticket-link view/edit flows in `scaffold/apps/threat/routes.py` and `scaffold/apps/risk/routes.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Assign multiple assets to a threat scenario (Priority: P1) 🎯 MVP

**Goal**: Let authorized users select and persist multiple threatened assets on a single threat scenario.

**Independent Test**: Edit or create a STRIDE scenario with multiple assets, save it, reopen it, and confirm every selected asset persists and appears on review surfaces.

### Tests for User Story 1 ⚠️

- [X] T008 [P] [US1] Add regression coverage for multi-asset scenario create/edit persistence, legacy single-assignment no-op saves, and preserved historical unavailable assets in `tests/test_threat_routes.py`

### Implementation for User Story 1

- [X] T009 [US1] Change the threat scenario asset input to multi-select in `scaffold/apps/threat/forms.py` and `scaffold/apps/threat/templates/threat/scenario_form.html`
- [X] T010 [US1] Persist and prefill multiple asset assignments, including preserved read-only historical assets and legacy single-assignment saves, in `scaffold/apps/threat/routes.py`
- [X] T011 [US1] Render multiple assets on the scenario detail flow, including read-only historical assets, in `scaffold/apps/threat/routes.py` and `scaffold/apps/threat/templates/threat/scenario_detail.html`
- [X] T012 [US1] Update audit details for asset add/remove changes and translated help/error copy for multi-asset edits in `scaffold/apps/threat/routes.py`, `scaffold/translations/en.json`, and `scaffold/translations/nl.json`

**Checkpoint**: User Story 1 should now be independently functional and testable.

---

## Phase 4: User Story 2 - Assign multiple STRIDE-LM categories to a threat scenario (Priority: P2)

**Goal**: Let STRIDE scenarios persist multiple STRIDE-LM categories without breaking non-STRIDE methodology flows.

**Independent Test**: Edit or create a STRIDE scenario with multiple STRIDE-LM categories, save it, reopen it, and confirm the selections persist while non-STRIDE methodology fields still behave correctly.

### Tests for User Story 2 ⚠️

- [X] T013 [P] [US2] Add regression coverage for multi-category STRIDE scenario create/edit persistence, audit visibility, and preserved historical unavailable categories in `tests/test_threat_routes.py`

### Implementation for User Story 2

- [X] T014 [US2] Change the STRIDE-LM category input to multi-select while preserving methodology toggles in `scaffold/apps/threat/forms.py` and `scaffold/apps/threat/templates/threat/scenario_form.html`
- [X] T015 [US2] Persist, prefill, and audit multiple STRIDE-LM category assignments, including preserved read-only historical categories, in `scaffold/apps/threat/routes.py`
- [X] T016 [US2] Update STRIDE-specific validation and translated copy for multi-category selection in `scaffold/apps/threat/routes.py`, `scaffold/translations/en.json`, and `scaffold/translations/nl.json`
- [X] T017 [US2] Preserve compatible PASTA, LINDDUN, and OWASP behavior alongside plural STRIDE categories in `scaffold/apps/threat/routes.py` and `scaffold/apps/threat/templates/threat/scenario_form.html`

**Checkpoint**: User Story 2 should now be independently functional and testable.

---

## Phase 5: User Story 3 - Review multi-assigned scenarios clearly (Priority: P3)

**Goal**: Make dashboards, detail views, and exports clearly show all assigned assets and STRIDE-LM categories for each scenario.

**Independent Test**: Seed a scenario with multiple assets and categories, then verify the detail page, model/dashboard summaries, and CSV/HTML/PDF outputs all present the full assignment set clearly.

### Tests for User Story 3 ⚠️

- [X] T018 [P] [US3] Add regression coverage for multi-assigned scenario review and export surfaces in `tests/test_threat_routes.py`

### Implementation for User Story 3

- [X] T019 [US3] Update dashboard and model-detail grouping for plural STRIDE-LM categories in `scaffold/apps/threat/routes.py`, `scaffold/apps/threat/templates/threat/dashboard.html`, and `scaffold/apps/threat/templates/threat/model_detail.html`
- [X] T020 [US3] Render shortened interactive summaries with full-list access on detail and dashboard surfaces, and render full assigned asset/category lists in export templates in `scaffold/apps/threat/templates/threat/scenario_detail.html`, `scaffold/apps/threat/templates/threat/model_detail.html`, and `scaffold/apps/threat/templates/threat/export_report.html`
- [X] T021 [US3] Extend threat CSV export with plural asset/category columns and compatibility aliases in `scaffold/apps/threat/services.py`
- [X] T022 [US3] Update translated review/export labels for plural assignments in `scaffold/translations/en.json` and `scaffold/translations/nl.json`

**Checkpoint**: User Story 3 should now be independently functional and testable.

---

## Phase 6: User Story 4 - Attach multiple ticket links to a risk (Priority: P3)

**Goal**: Let users add, persist, review, and API-serialize multiple labeled ticket links on each risk.

**Independent Test**: Edit or create a risk with two labeled URLs, save it, reopen it, view it on the dashboard, and confirm the API returns the plural `ticket_links` structure plus the deprecated compatibility alias.

### Tests for User Story 4 ⚠️

- [X] T023 [P] [US4] Add route and API regression coverage for multiple labeled ticket links, audit visibility, and degraded saved-link review behavior in `tests/test_risk_routes.py` and `tests/test_risk_api.py`

### Implementation for User Story 4

- [X] T024 [US4] Replace the single ticket URL form handling with repeated labeled ticket-link inputs in `scaffold/apps/risk/forms.py` and `scaffold/apps/risk/templates/risk/form.html`
- [X] T025 [US4] Persist ordered risk ticket links, preserve previously saved degraded links for review, and audit add/remove/edit changes in create/edit flows in `scaffold/apps/risk/routes.py`
- [X] T026 [US4] Extend request/response compatibility for `ticket_links` and deprecated `ticket_url` in `scaffold/apps/risk/services.py` and `scaffold/apps/risk/api.py`
- [X] T027 [US4] Render multiple ticket links on the risk dashboard and edit review surfaces, including degraded-link status when detectable, in `scaffold/apps/risk/templates/risk/dashboard.html` and `scaffold/apps/risk/templates/risk/form.html`
- [X] T028 [US4] Update translated ticket-link labels and validation messages in `scaffold/translations/en.json` and `scaffold/translations/nl.json`

**Checkpoint**: User Story 4 should now be independently functional and testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final documentation, compatibility review, and validation across the feature.

- [ ] T029 [P] Document risk ticket-link and compatibility changes in `docs/risk.md` and `docs/history.md`
- [ ] T030 [P] Document threat multi-assignment review/export behavior in `docs/threat_modeling_plan.md` and `specs/001-threat-risk-update/quickstart.md`
- [ ] T031 Run the migration and focused test validation from `specs/001-threat-risk-update/quickstart.md` using `poetry run flask --app scaffold:create_app db upgrade` and `poetry run pytest tests/test_threat_routes.py tests/test_risk_routes.py tests/test_risk_api.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational phase completion.
- **Polish (Phase 7)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - no dependency on other stories.
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - no dependency on other stories.
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) using seeded multi-assignment data - no dependency on UI work from US1/US2.
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - independent of threat review stories.

### Within Each User Story

- Tests for behavior, security, data, and schema changes MUST be written or updated before implementation completes.
- Model and shared schema changes happen in Foundational before story-specific route/template work.
- Forms before routes when the story changes input capture.
- Route/service persistence before detail/dashboard/export rendering.
- Story-specific translations and audit updates complete before the story is considered done.

### Parallel Opportunities

- `T002` can run in parallel with `T001` after the migration filename is chosen.
- `T006` and `T007` can run in parallel after `T003` and `T004` define the new relationships.
- `T008`, `T013`, `T018`, and `T023` can be worked in parallel once Foundational completes.
- User Stories 1, 2, 3, and 4 can be implemented in parallel after Foundational if staffed.
- `T029` and `T030` can run in parallel once the final UI/API behavior is settled.

---

## Parallel Example: User Story 1

```bash
# Launch the User Story 1 test and form work in parallel:
Task: "Add regression coverage for multi-asset scenario create/edit persistence in tests/test_threat_routes.py"
Task: "Change the threat scenario asset input to multi-select in scaffold/apps/threat/forms.py and scaffold/apps/threat/templates/threat/scenario_form.html"
```

## Parallel Example: User Story 2

```bash
# Launch the User Story 2 test and validation work in parallel:
Task: "Add regression coverage for multi-category STRIDE scenario create/edit persistence in tests/test_threat_routes.py"
Task: "Update STRIDE-specific validation and translated copy for multi-category selection in scaffold/apps/threat/routes.py, scaffold/translations/en.json, and scaffold/translations/nl.json"
```

## Parallel Example: User Story 4

```bash
# Launch the User Story 4 route/API test and UI work in parallel:
Task: "Add route and API regression coverage for multiple labeled ticket links in tests/test_risk_routes.py and tests/test_risk_api.py"
Task: "Replace the single ticket URL form handling with repeated labeled ticket-link inputs in scaffold/apps/risk/forms.py and scaffold/apps/risk/templates/risk/form.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1.
4. Validate the multi-asset scenario flow independently before expanding scope.

### Incremental Delivery

1. Finish Setup + Foundational once.
2. Deliver User Story 1 for multi-asset threat scenarios.
3. Deliver User Story 2 for plural STRIDE-LM categorization.
4. Deliver User Story 3 for reviewer-visible summary/export improvements.
5. Deliver User Story 4 for plural risk ticket links.
6. Finish Polish with docs and validation.

### Parallel Team Strategy

1. One developer handles Phase 1 and Phase 2 schema/service groundwork.
2. After Foundational completes:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
   - Developer D: User Story 4
3. Merge into Phase 7 for documentation and validation.

---

## Notes

- `[P]` tasks touch different files and can proceed without depending on an incomplete sibling task.
- `[US1]` through `[US4]` map directly to the clarified spec stories for traceability.
- The migration/backfill work is intentionally centralized in Phase 2 so every story builds on the same persisted model shape.
- Keep deprecated compatibility aliases (`ticket_url`, single export columns) only as long as the release plan requires them.