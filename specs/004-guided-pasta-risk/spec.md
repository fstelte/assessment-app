# Feature Specification: Guided PASTA Risk Analysis

**Feature Branch**: `[004-guided-pasta-risk]`

**Created**: 2026-06-08

**Status**: Draft

**Input**: User description: "for the PASTA threat modeling I want a more guided experience. During the risk and impact analysis everything should come together. As stated in https://threat-modeling.com/pasta-threat-modeling/ in the table. So it should also have a likelihood and impact score (simular to the stride functionality). The data should also be plotted into the risk workspace, also the reporting should be made in the same style of the application."

## Clarifications

### Session 2026-06-08

- Q: How should finalized PASTA risk conclusions reach the risk workspace? → A: PASTA conclusions stay inside the threat model until a user explicitly publishes them to the risk workspace.
- Q: Which record is authoritative after a PASTA risk conclusion is published? → A: PASTA remains the source of truth, and the risk-workspace entry is a linked projection refreshed by republishing.
- Q: When is a PASTA risk conclusion publishable to the risk workspace? → A: A PASTA risk conclusion is publishable when it has likelihood, impact, overall risk outcome, and no active revalidation flag.
- Q: Which reporting surfaces are required in v1? → A: V1 reporting includes the interactive UI plus the existing HTML, PDF, and CSV outputs.
- Q: Which users can publish or republish PASTA risk conclusions to the risk workspace? → A: Any user who can edit the PASTA model can also publish and republish its risk conclusions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete a guided PASTA analysis from stage inputs to final risk conclusions (Priority: P1)

An authorized assessment user can move through PASTA with clear guidance at each stage so that the final risk and impact analysis consolidates the relevant business, technical, threat, vulnerability, and attack information instead of requiring the user to reconstruct it manually.

**Why this priority**: The main user need is a more guided PASTA experience where the methodology leads naturally to an actionable risk outcome.

**Independent Test**: Can be fully tested by creating a PASTA model, progressing through the stages with stage-specific prompts and saved findings, and confirming that stage seven presents the accumulated upstream analysis for final risk and impact review.

**Acceptance Scenarios**:

1. **Given** an authorized user starts a PASTA model, **When** they move from one stage to the next, **Then** the workflow shows the expected stage purpose, the information still needed, and the outputs that will feed later stages.
2. **Given** the user reaches Risk and Impact Analysis, **When** they open stage seven, **Then** the workflow presents the relevant objectives, scope, decomposition, threats, vulnerabilities, and attack-path evidence gathered earlier in the model.
3. **Given** earlier-stage findings change after a stage-seven draft exists, **When** the user returns to Risk and Impact Analysis, **Then** the workflow clearly shows which conclusions need review before they are treated as current.

---

### User Story 2 - Score PASTA risk conclusions and publish them to the risk workspace (Priority: P2)

An authorized assessment user can assign likelihood and impact scores to final PASTA risk conclusions and publish those results into the existing risk workspace so the organization can compare, prioritize, and track them alongside related risk records.

**Why this priority**: The user explicitly wants the later PASTA analysis to produce scored risk output similar to the existing STRIDE-based experience and to make that output visible where risk work already happens.

**Independent Test**: Can be fully tested by completing a PASTA risk conclusion with likelihood and impact scoring, explicitly publishing it to the risk workspace, and confirming that the resulting risk data appears there with traceability back to the source PASTA model.

**Acceptance Scenarios**:

1. **Given** a PASTA model has sufficient stage-seven evidence, **When** the user records a final risk conclusion, **Then** they can assign both a likelihood score and an impact score using the same scoring language already familiar from the existing threat-risk workflow.
2. **Given** a scored PASTA risk conclusion has likelihood, impact, overall risk outcome, and no active revalidation flag, **When** a user with permission to edit the PASTA model publishes it to the risk workspace, **Then** the risk appears there with its score values, overall priority, and a link back to the originating PASTA analysis.
3. **Given** the user updates a previously published PASTA risk conclusion, **When** a user with permission to edit the PASTA model publishes the updated conclusion again, **Then** the workspace refreshes the existing linked risk without creating a duplicate entry for the same conclusion and without making the risk workspace the new source of truth.

---

### User Story 3 - Review and export PASTA results in the same application style (Priority: P3)

A reviewer can consume guided PASTA findings, final risk scoring, and linked risk-workspace output through review and reporting surfaces that match the rest of the application so the analysis is credible, consistent, and easy to share.

**Why this priority**: Reporting is part of the requested outcome, and inconsistent presentation would make the new workflow feel disconnected from the rest of the platform.

**Independent Test**: Can be fully tested by reviewing a completed PASTA model in the interactive UI and in supported report outputs and confirming that the layout, terminology, and visual treatment align with existing application patterns.

**Acceptance Scenarios**:

1. **Given** a completed or partially completed guided PASTA model, **When** a reviewer opens it, **Then** they can understand stage progress, final risk conclusions, and their relationship to the risk workspace without reading raw edit screens.
2. **Given** a reviewer exports or shares a PASTA analysis, **When** they use the supported v1 reporting surfaces, **Then** the interactive UI and the existing HTML, PDF, and CSV outputs present the stage outputs, risk scores, and risk-workspace links in the same style and structure used elsewhere in the application.
3. **Given** a PASTA conclusion is still incomplete, **When** it appears in review or reporting, **Then** the output makes the draft status explicit rather than implying a finalized risk decision.

---

### Edge Cases

- If the user reaches Risk and Impact Analysis without enough upstream evidence to support a credible conclusion, the workflow keeps the stage accessible for review but clearly marks what is still missing before scoring can be finalized.
- If multiple attack paths or vulnerabilities contribute to one business risk, the workflow allows them to support a single final risk conclusion without forcing duplicate risk entries.
- If a PASTA risk conclusion is already present in the risk workspace, publishing a revised conclusion updates the existing linked risk view rather than creating a second independent copy.
- If a reviewer edits fields in the risk workspace that originated from a published PASTA conclusion, the workflow preserves PASTA as the authoritative source and requires a republish or explicit traceable override pattern rather than silently splitting the records.
- If a PASTA risk conclusion is missing likelihood, impact, overall risk outcome, or has an active revalidation flag, it remains reviewable inside PASTA but cannot be published to the risk workspace yet.
- If a user can edit guided PASTA content but loses edit permission before publication, the workflow blocks new publication or republication attempts until edit permission is restored.
- If a user removes or materially changes upstream threat, vulnerability, or attack analysis after scoring a risk, the linked risk remains traceable but is marked for revalidation until the source conclusion is reviewed.
- If a reviewer opens a model that has guided stage content but no finalized risk score yet, the UI and reporting still distinguish draft findings from completed risk conclusions.
- If a PASTA finding does not map cleanly to an existing STRIDE-style category, the guided workflow still allows the risk conclusion to be recorded and reported.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a more guided PASTA workflow within the existing threat modeling experience rather than leaving users to infer the process from generic free-text fields.
- **FR-002**: The system MUST preserve the seven canonical PASTA stages and present each stage with clear guidance about its purpose, the expected inputs, and the output that feeds later stages.
- **FR-003**: The system MUST save stage-specific findings across the full guided PASTA workflow so users can pause, resume, and review their work over multiple sessions.
- **FR-004**: The system MUST make the Risk and Impact Analysis stage the point where the relevant outputs from the prior PASTA stages are brought together for final evaluation.
- **FR-005**: The system MUST show the upstream objectives, technical scope, decomposition findings, threat analysis, vulnerability findings, and attack analysis evidence that support each final risk conclusion.
- **FR-006**: The system MUST allow authorized users to record one or more final PASTA risk conclusions from the stage-seven analysis.
- **FR-007**: Each final PASTA risk conclusion MUST support both a likelihood score and an impact score.
- **FR-008**: The likelihood and impact scoring used for final PASTA risk conclusions MUST follow the same scoring scale and interpretation already used in the existing STRIDE-style risk workflow so users can compare results consistently.
- **FR-009**: The system MUST derive or present an overall risk priority from the recorded likelihood and impact values using the existing risk-evaluation approach already familiar in the application.
- **FR-010**: The system MUST preserve traceability from each final PASTA risk conclusion back to the supporting threats, vulnerabilities, attack paths, assets, and business objectives captured earlier in the model.
- **FR-011**: The system MUST allow users with permission to edit the PASTA model to publish final PASTA risk conclusions into the existing risk workspace without requiring users to re-enter the same risk information manually.
- **FR-011A**: A PASTA risk conclusion MUST be publishable only when it includes likelihood, impact, an overall risk outcome, and no active revalidation flag.
- **FR-012**: Risk-workspace entries published from PASTA MUST remain linked to the source PASTA conclusion so reviewers can navigate between the threat analysis and the risk view.
- **FR-013**: When a previously published PASTA risk conclusion changes, the system MUST allow an authorized user to refresh the corresponding risk-workspace projection without creating duplicate risk entries for the same source conclusion.
- **FR-013A**: Published risk-workspace entries derived from PASTA MUST be treated as linked projections of the source PASTA conclusion rather than as a second authoritative record for the same analysis.
- **FR-013B**: The system MUST preserve PASTA as the authoritative source for published PASTA risk fields that originate from stage-seven analysis and scoring.
- **FR-014**: The system MUST make it clear in the risk workspace when a linked PASTA risk conclusion is current, draft, or awaiting revalidation because upstream analysis changed.
- **FR-015**: The system MUST continue to support existing STRIDE-based workflows and preserve comparability between STRIDE-derived and PASTA-derived risk scoring.
- **FR-016**: The system MUST present guided PASTA review screens and reports in the same visual style, terminology quality, and structural conventions used elsewhere in the application.
- **FR-017**: The system MUST make guided PASTA analyses reviewable in the interactive UI and in the existing HTML, PDF, and CSV reporting outputs used for this domain.
- **FR-018**: Review and reporting outputs MUST show stage progress, final likelihood and impact scores, overall risk priority, and any linked risk-workspace presence in a way that is understandable to business and technical reviewers.
- **FR-019**: The system MUST explicitly distinguish draft or incomplete PASTA risk conclusions from finalized risk conclusions in both review and reporting surfaces.
- **FR-020**: The system MUST enforce the existing role-based permissions for creating, editing, reviewing, and operationalizing PASTA threat-model content and linked risk output.
- **FR-020A**: Publication and republication of PASTA risk conclusions to the risk workspace MUST follow the same edit permission model used for the source PASTA model rather than requiring an additional elevated publish-only role.
- **FR-021**: The system MUST record attributable audit history for guided-stage updates, likelihood and impact scoring changes, and publication or synchronization of linked risk-workspace entries.
- **FR-022**: The system MUST localize the new guided PASTA labels, instructions, validation messages, scoring terminology, and reporting text introduced by this feature.

### Key Entities *(include if feature involves data)*

- **Guided PASTA Model**: A threat-model record that leads users through the seven PASTA stages with saved stage guidance and outputs.
- **Stage Guidance State**: The per-stage status that captures what has been completed, what still needs attention, and whether later risk conclusions require revalidation.
- **PASTA Risk Conclusion**: The stage-seven outcome that summarizes the business risk, supporting analysis, mitigation context, and final scoring for one identified risk.
- **PASTA Risk Score**: The pair of likelihood and impact values, plus the resulting overall priority, attached to a final PASTA risk conclusion.
- **Risk Workspace Link**: The traceable relationship between a PASTA risk conclusion as source of truth and its published projection in the existing risk workspace.
- **Reporting View**: The reviewable representation of guided stage outputs, final scores, and linked risk records across the supported application reporting surfaces.

## Security, Audit, and Operations *(mandatory)*

- **Authorization Impact**: Guided PASTA creation, scoring, review, and linked risk-workspace publication follow the same existing role checks already enforced for threat workflows, including allowing PASTA editors to publish and republish their risk conclusions.
- **Audit/Event Impact**: The audit trail must capture guided-stage progress changes, final likelihood and impact scoring changes, creation or refresh of linked risk-workspace projections, and final risk conclusion updates.
- **Data Sensitivity Impact**: Guided PASTA records and linked risk output may contain sensitive architecture, vulnerability, attack-path, and business-impact information and remain subject to existing threat and risk access controls.
- **Migration/Backfill Impact**: The feature may require additional persisted state for guided PASTA conclusions, scoring, and risk-workspace linkage while preserving existing PASTA and STRIDE records and their review history.
- **Localization Impact**: New guidance text, scoring labels, stage-seven summary terminology, risk-workspace indicators, and reporting copy require translation coverage.
- **Deployment/Configuration Impact**: Release guidance must cover how guided PASTA conclusions appear in the risk workspace, how revalidation status should be interpreted, and how reporting differs between draft and finalized risk conclusions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of acceptance-test runs, an authorized user can complete a guided PASTA analysis through stage seven and reopen it later without loss of stage guidance, findings, or final scoring.
- **SC-002**: In at least 90% of validation sessions using a representative assessment, users can reach an initial scored stage-seven conclusion in under 25 minutes because the workflow presents the required upstream evidence in context.
- **SC-003**: In 100% of test scenarios with finalized PASTA risk conclusions, reviewers can see both likelihood and impact scores and the resulting overall risk priority without consulting raw edit history.
- **SC-004**: In 100% of linked-risk validation scenarios, finalized PASTA risk conclusions can be explicitly published into the existing risk workspace with traceability back to the source analysis and without duplicate entries for the same conclusion.
- **SC-004A**: In 100% of publication-gating validation scenarios, PASTA risk conclusions that are incomplete or marked for revalidation are blocked from risk-workspace publication until they are current.
- **SC-005**: In 100% of review and export validation scenarios, guided PASTA reports match the application's established review style closely enough that users can recognize them as part of the same platform experience.
- **SC-005A**: In 100% of supported v1 reporting scenarios, guided PASTA analyses are available in the interactive UI and in the existing HTML, PDF, and CSV outputs.
- **SC-006**: In 100% of audited validation scenarios, changes to guided-stage state, final scores, and linked risk-workspace publication produce attributable audit records.

## Assumptions

- The existing threat modeling and risk workspace features already have an established likelihood-and-impact scoring approach that PASTA should reuse rather than redefine.
- The guided experience builds on the existing PASTA workflow work already planned for the threat module rather than replacing PASTA with a different methodology.
- Final PASTA risk conclusions are the unit that should be publishable to the risk workspace, not every intermediate stage finding.
- Published risk-workspace records derived from PASTA remain downstream projections of the PASTA conclusion rather than becoming the primary record for PASTA-specific scoring and traceability.
- Publishability is determined by completion of the stage-seven scoring fields and the absence of an active revalidation requirement rather than by a separate approval workflow.
- No separate elevated publish role is introduced for v1; users who can edit the PASTA model can publish or republish its eligible risk conclusions.
- The risk workspace can already display risk priority in a way that PASTA-linked results can join without introducing a separate reporting paradigm.
- Supported reporting outputs for this domain remain the interactive UI and the current HTML, PDF, and CSV surfaces rather than a new standalone reporting subsystem.
- Existing STRIDE-based assessments remain valid and continue to coexist with guided PASTA analysis.