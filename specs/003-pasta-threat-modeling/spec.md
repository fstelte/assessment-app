# Feature Specification: PASTA Threat Modeling

**Feature Branch**: `[003-extend-pasta-modeling]`

**Created**: 2026-06-07

**Status**: Draft

**Input**: User description: "threat moddeling based on PASTA. As extention to STRIDE-LM. PASTA will use STRIDE-LM where possible (base the improment on https://threat-modeling.com/pasta-threat-modeling/)"

## Clarifications

### Session 2026-06-07

- Q: How should users progress through the seven PASTA stages? → A: Use ordered stages with light gating: later stages unlock after the prior stage meets its defined minimum-content threshold, and earlier stages remain editable.
- Q: How should PASTA connect to existing downstream mitigation and follow-up workflows? → A: PASTA keeps its own stage records, and selected threat findings can generate or link standard threat scenarios for downstream workflows.
- Q: How should methodology switching work between STRIDE-LM and PASTA? → A: Allow one-way conversion from an existing STRIDE-LM model into a PASTA model bootstrap.
- Q: Which review surfaces are required for PASTA in v1? → A: PASTA must be reviewable in the interactive UI and in the existing HTML, PDF, and CSV threat export surfaces.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a PASTA threat model through all seven stages (Priority: P1)

An authorized assessment user can create and maintain a threat model that follows the full PASTA process so the organization can analyze threats in a risk-centric way from business objectives through impact and mitigation.

**Why this priority**: The core value of this feature is enabling a complete PASTA-based analysis workflow rather than forcing users to approximate PASTA with free-text notes or a STRIDE-only structure.

**Independent Test**: Can be fully tested by creating a new PASTA threat model, progressing through all seven stages, saving findings at each stage, and confirming the model can be reviewed later with stage-specific outputs intact.

**Acceptance Scenarios**:

1. **Given** an authorized user starts a new threat model, **When** they choose the PASTA methodology, **Then** the workflow presents the seven PASTA stages in order: Define the Objectives, Define the Technical Scope, Decompose the Application, Analyze the Threats, Vulnerability Analysis, Attack Analysis, and Risk and Impact Analysis.
2. **Given** a PASTA model contains saved stage findings, **When** the user leaves and later reopens the model, **Then** the saved stage progress and findings remain available for continued work and review.
3. **Given** a user has entered the defined minimum-content threshold for the current PASTA stage, **When** they continue the workflow, **Then** the next stage becomes available while previously completed stages remain editable.

---

### User Story 2 - Reuse STRIDE-LM where it strengthens PASTA analysis (Priority: P2)

An authorized assessment user can reuse relevant STRIDE-LM classifications and existing threat-model context within the PASTA workflow so the team avoids duplicate analysis and keeps methodology-specific outputs aligned.

**Why this priority**: The user explicitly wants PASTA to extend the current STRIDE-LM capability rather than replace it. Reuse reduces duplicate effort and keeps existing threat-model assets valuable.

**Independent Test**: Can be fully tested by creating or editing a PASTA model that references existing threat-model context, linking relevant STRIDE-LM categories where applicable, and confirming those links remain visible without forcing STRIDE-LM mapping for every stage.

**Acceptance Scenarios**:

1. **Given** a PASTA stage produces threat findings that align with existing STRIDE-LM classifications, **When** the user records those findings, **Then** they can associate the relevant STRIDE-LM categories without re-entering the same threat context from scratch.
2. **Given** a PASTA stage has no meaningful STRIDE-LM mapping, **When** the user records the stage outcome, **Then** the workflow allows the PASTA finding to stand on its own without blocking completion.

---

### User Story 3 - Review PASTA results as actionable business risk output (Priority: P3)

A reviewer can understand the business context, threats, vulnerabilities, attack paths, and resulting risk posture captured by a PASTA model so they can prioritize mitigation and communicate the analysis clearly.

**Why this priority**: PASTA is valuable because it connects technical threat analysis to business impact. Review surfaces must make that connection clear or the feature loses its purpose.

**Independent Test**: Can be fully tested by reviewing a completed PASTA model and confirming that stage outputs, linked STRIDE-LM context, and final risk-impact conclusions are all distinguishable and understandable without opening raw edit screens.

**Acceptance Scenarios**:

1. **Given** a completed or partially completed PASTA model, **When** a reviewer opens it, **Then** they can see the findings for each completed stage and the current completion state of the remaining stages.
2. **Given** the model includes both PASTA-native findings and STRIDE-LM-supported classifications, **When** a reviewer examines the analysis, **Then** they can distinguish the PASTA stage outputs from the reused STRIDE-LM context.
3. **Given** a PASTA model contains threat findings that need downstream treatment, **When** an authorized user chooses to operationalize those findings, **Then** the workflow can generate or link standard threat scenarios without collapsing all PASTA stage content into standard threat-scenario records.
4. **Given** a reviewer needs to share or archive a PASTA analysis, **When** they use the supported threat-model review outputs, **Then** the PASTA model is reviewable in the interactive UI and in the existing HTML, PDF, and CSV export surfaces.

---

### Edge Cases

- If a user bootstraps a new PASTA model from an existing STRIDE-LM model, the workflow preserves reusable context in the new PASTA model, keeps that copied context editable, and leaves the original STRIDE-LM model unchanged as a separate reviewable record.
- If a PASTA stage is incomplete, the model remains reviewable and resumable without being mistaken for a completed analysis.
- If existing threat-model assets, trust-boundary information, or threat classifications are unavailable for reuse, the PASTA workflow still allows manual completion of the affected stage.
- If a PASTA finding aligns to more than one STRIDE-LM category, the workflow preserves all relevant mappings without collapsing them to a single label.
- If a PASTA stage produces no relevant STRIDE-LM mapping, the absence of a mapping does not block the stage from being saved.
- If an existing STRIDE-LM-only model is opened after this feature is released, it remains usable without forcing conversion to PASTA.
- If a reviewer accesses a partially completed PASTA model, the workflow makes incomplete stages explicit so missing analysis is not interpreted as no risk.
- If a PASTA finding has already generated or linked a standard threat scenario, the workflow preserves the relationship so reviewers can tell which downstream record came from which PASTA analysis item.
- If a user revisits an earlier PASTA stage after later stages have been opened, the workflow preserves later-stage content but marks later vulnerability, attack, and risk outputs for revalidation when objectives, scoped assets, trust boundaries, dependencies, or threat findings change.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support PASTA as a first-class threat-modeling methodology alongside the existing methodologies already available in the threat modeling workspace.
- **FR-002**: The system MUST structure PASTA threat modeling around these seven stages: Define the Objectives, Define the Technical Scope, Decompose the Application, Analyze the Threats, Vulnerability Analysis, Attack Analysis, and Risk and Impact Analysis.
- **FR-003**: The system MUST allow authorized users to create, save, edit, and review stage-specific findings for each PASTA stage.
- **FR-003A**: The system MUST present PASTA as an ordered stage workflow with light gating, where each later stage unlocks only after the immediately preceding stage contains the required minimum content for that stage.
- **FR-003B**: For v1, the minimum required content for stage progression MUST be: Define the Objectives requires at least one business or security objective and a short scope statement; Define the Technical Scope requires at least one in-scope asset or interface and one trust-boundary, dependency, or integration note; Decompose the Application requires at least one component, process, or data-flow element relevant to the model; Analyze the Threats requires at least one threat finding; Vulnerability Analysis requires at least one vulnerability finding or an explicit "none identified" outcome; Attack Analysis requires at least one attack-path finding or an explicit "no credible path identified" outcome; and Risk and Impact Analysis requires at least one summarized risk conclusion.
- **FR-004**: The system MUST preserve stage progress and saved findings so a PASTA model can be resumed and reviewed over multiple sessions.
- **FR-004A**: The system MUST allow users to return to and edit earlier PASTA stages after later stages have been unlocked.
- **FR-005**: The system MUST allow users to capture business objectives, security objectives, compliance context, and business-impact considerations as part of the PASTA workflow.
- **FR-006**: The system MUST allow users to capture technical scope, dependencies, trust boundaries, interfaces, and assets as part of the PASTA workflow.
- **FR-007**: The system MUST allow users to capture threat agents, threat scenarios, vulnerability findings, attack-path analysis, and resulting business risk within the same PASTA model.
- **FR-007A**: The system MUST preserve PASTA stage records as methodology-specific artifacts rather than automatically flattening all stage findings into the standard threat-scenario structure.
- **FR-008**: The system MUST reuse existing threat-model context, such as assets, threat scenarios, and related analysis inputs, when that context is relevant to the active PASTA stage.
- **FR-009**: When a PASTA finding aligns with existing STRIDE-LM categories, the system MUST allow the user to associate those categories with the PASTA finding.
- **FR-010**: The system MUST make STRIDE-LM reuse optional at the finding level and MUST NOT require a STRIDE-LM mapping for PASTA stages or findings where no meaningful mapping exists.
- **FR-011**: The system MUST distinguish PASTA stage outputs from reused STRIDE-LM classifications in review and reporting surfaces.
- **FR-012**: The system MUST allow reviewers to see the completion state of each PASTA stage and the current overall state of the model.
- **FR-013**: The system MUST preserve existing STRIDE-LM-only threat models and related workflows without requiring users to migrate or convert them as part of this feature.
- **FR-013A**: The system MUST allow authorized users to bootstrap a new PASTA model from an existing STRIDE-LM model through a one-way conversion flow that reuses relevant existing context.
- **FR-013B**: The system MUST NOT require or support general bidirectional methodology switching on the same threat-model record after a PASTA model has been created.
- **FR-014**: The system MUST enforce the existing role-based access rules for creating, editing, and reviewing threat models when PASTA methodology is used.
- **FR-015**: The system MUST record attributable audit history for creation and material updates of PASTA models, including changes to stage findings and final risk conclusions.
- **FR-016**: The system MUST support review outputs that summarize stage findings, reused STRIDE-LM context, and final risk-impact conclusions in a form suitable for stakeholder review.
- **FR-016B**: The system MUST make PASTA models reviewable in the interactive threat-model UI and in the existing HTML, PDF, and CSV threat export surfaces for v1.
- **FR-016A**: The system MUST allow authorized users to generate or link standard threat scenarios from selected PASTA threat findings when downstream mitigation, treatment, or follow-up workflows require the standard threat-scenario form.
- **FR-017**: The system MUST localize new user-facing labels, stage names, guidance text, validation messages, and review terminology introduced for PASTA.
- **FR-018**: The system MUST make incomplete or draft PASTA stages explicit in the user experience so reviewers do not interpret missing stage output as a completed low-risk conclusion.
- **FR-018A**: When edits to an earlier PASTA stage materially affect later-stage analysis, the system MUST clearly mark the affected later-stage content for revalidation before it is treated as current.
- **FR-018B**: For v1, revalidation MUST be triggered when a user changes an earlier-stage objective, in-scope asset, trust boundary, major dependency, or threat finding in a way that could invalidate downstream vulnerability analysis, attack analysis, or risk conclusions.
- **FR-019**: The system MUST allow a PASTA model to capture multiple relevant STRIDE-LM mappings for a single finding when the analysis supports more than one category.
- **FR-020**: The system MUST support linking final PASTA risk conclusions to the platform's existing mitigation and follow-up workflows wherever threat-model outputs already feed downstream review or treatment activities.
- **FR-020A**: The system MUST preserve traceability between a PASTA finding and any generated or linked standard threat scenario used in downstream workflows.

### Key Entities *(include if feature involves data)*

- **PASTA Threat Model**: A threat-model record that uses the PASTA methodology and organizes analysis across seven ordered stages.
- **PASTA Stage Record**: A stage-specific portion of a PASTA model that captures completion state, findings, and reviewable outcomes for one of the seven stages.
- **PASTA Finding**: A documented output from a PASTA stage, such as an objective, scoped asset, threat, vulnerability, attack path, or business-impact conclusion.
- **Generated Threat Scenario Link**: A traceable relationship between a selected PASTA threat finding and a standard threat scenario record used by existing downstream workflows.
- **STRIDE-LM Mapping**: A relationship that connects a PASTA finding to one or more relevant STRIDE-LM categories when the methodologies overlap meaningfully.
- **Risk Conclusion**: The summarized business risk, impact, and mitigation-oriented outcome produced by the later stages of a PASTA model.

## Security, Audit, and Operations *(mandatory)*

- **Authorization Impact**: PASTA model creation, editing, and review follow the same existing threat-model access rules already used for authorized editors and reviewers.
- **Audit/Event Impact**: Creation of a PASTA model, material changes to stage findings, methodology changes, and final risk conclusions must be attributable in the audit trail.
- **Data Sensitivity Impact**: PASTA models may contain sensitive system scope, business impact, vulnerability, and attack-path information and must remain subject to existing access, export, and retention controls for threat-model data.
- **Migration/Backfill Impact**: Existing STRIDE-LM models remain valid without mandatory conversion. Any new PASTA data structure must preserve existing threat-model records and historical reviewability, and any bootstrap flow must preserve the original STRIDE-LM model as a separate historical record rather than replacing it in place.
- **Localization Impact**: New PASTA stage labels, guidance, validation copy, review text, methodology-selection text, and any new export terminology require translation support.
- **Deployment/Configuration Impact**: Release planning must cover operator guidance for when to use PASTA versus STRIDE-LM, how reused STRIDE-LM mappings appear in review outputs, and how downstream reviewers should interpret partially completed PASTA models.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of acceptance-test runs, an authorized user can create a PASTA threat model, save findings in all seven stages, and reopen the model without loss of stage data.
- **SC-002**: In at least 90% of timed validation sessions using the reference scenario of one in-scope application with at least three assets, two trust boundaries, two documented integrations or dependencies, and one existing threat-model context source available for optional reuse, users can complete an initial first pass through the first four PASTA stages in under 20 minutes.
- **SC-003**: In 100% of review scenarios, reviewers can distinguish PASTA stage outputs from reused STRIDE-LM mappings without needing access to raw edit history.
- **SC-003A**: In 100% of supported v1 review scenarios, reviewers can access PASTA analyses through the interactive UI and through the HTML, PDF, and CSV threat export surfaces.
- **SC-004**: In 100% of audited test scenarios, creation and material updates of PASTA models produce attributable audit records.
- **SC-005**: In 100% of regression-test scenarios covering existing STRIDE-LM models, users can continue to view and edit those models without being forced into the PASTA workflow.

## Assumptions

- PASTA is added as an additional methodology within the existing threat modeling domain rather than as a separate standalone module.
- Existing threat-model assets, scenarios, and related context remain the primary reuse surface for PASTA where overlap exists.
- Existing STRIDE-LM models may serve as a bootstrap source for a new PASTA model, but methodology conversion is one-way and does not turn one record into a dual-mode model.
- STRIDE-LM remains available as a supporting classification lens for relevant PASTA findings, but PASTA remains the primary organizing methodology for this feature.
- Each PASTA stage will have a defined minimum required content threshold that is sufficient to unlock the next stage without forcing the entire model to be complete in a single pass.
- Only selected PASTA threat findings that benefit from downstream treatment need to generate or link standard threat scenarios; not every stage artifact needs a downstream record.
- Reviewers need visibility into both stage progress and final risk conclusions, even when a PASTA analysis is not yet complete.
- Existing audit, authorization, export, translation, and downstream mitigation patterns for threat-model data will be reused wherever applicable.
- V1 export support is limited to the existing HTML, PDF, and CSV threat-model export surfaces.
