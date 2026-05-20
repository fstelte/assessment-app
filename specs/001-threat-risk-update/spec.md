# Feature Specification: Threat Model and Risk Updates

**Feature Branch**: `[001-run-feature-hook]`

**Created**: 2026-05-20

**Status**: Draft

**Input**: User description: "Threat model update and Risk update"

## Clarifications

### Session 2026-05-20

- Q: What is the primary goal for this feature? → A: Multiselect for threat assets and categories.
- Q: What does "category" mean in this feature? → A: Threat categories on the threat scenario itself.
- Q: Should multiple ticket links on risks be included in this feature? → A: Yes, include multiple ticket links on risks in the same feature.
- Q: How should ticket links be stored on risks? → A: Store a short label plus a URL for each ticket link.
- Q: Which category model should this feature use? → A: The existing STRIDE-LM threat categories.
- Q: How should duplicate ticket links be identified for the same risk? → A: Duplicates are blocked only when both label and URL are identical.
- Q: What minimum selections are required before saving a STRIDE scenario? → A: Require at least one asset and at least one STRIDE-LM category.
- Q: How should saved threat assignments behave after reopen? → A: Membership is preserved; display order does not carry business meaning.
- Q: Which users may edit versus only review multi-assignments and ticket links? → A: Existing threat and risk managers keep edit access, while authorized reviewers keep read-only access.
- Q: Which review surfaces are mandatory for multi-assignments and ticket links? → A: Threat detail, threat dashboard/model summary, threat CSV export, threat HTML/PDF export, risk detail/edit review, risk dashboard, and risk API output.
- Q: What compatibility guarantee is required for legacy export and API consumers? → A: Deprecated compatibility aliases remain available in threat exports and the risk API for one release cycle.
- Q: Are ticket links optional or required on risks? → A: Ticket links are optional for all risks.
- Q: What is the maximum length for a risk ticket-link short label? → A: 80 characters maximum.
- Q: How should non-STRIDE methodologies behave after this feature ships? → A: Only STRIDE gains multi-category support; PASTA, LINDDUN, and OWASP keep current behavior.
- Q: How should archived or unavailable assets behave on existing scenarios? → A: Preserve them as read-only historical associations, but do not allow new selection or re-selection.
- Q: How should unavailable STRIDE-LM categories behave on existing scenarios? → A: Preserve them as read-only historical associations, but do not allow new selection or re-selection.
- Q: How should existing single-assignment scenarios behave when saved without multiselect changes? → A: Preserve them and save successfully without forcing reassignment.
- Q: How should crowded multi-assignment displays behave in interactive views and exports? → A: Interactive views show a shortened inline summary with access to the full list, while exports always show the full list.
- Q: How should saved ticket links behave when they become malformed, removed, or unreachable later? → A: Preserve them for review, flag them when detectable, and allow users to edit or remove them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Assign multiple assets to a threat scenario (Priority: P1)

An assessment manager creating or editing a threat scenario can select more than one affected asset so the scenario accurately represents threats that span multiple components, data flows, or trust boundaries.

**Why this priority**: Threat scenarios often affect multiple parts of the modeled system. Without multiselect support, users have to duplicate scenarios or leave part of the scope undocumented.

**Independent Test**: Can be fully tested by editing a threat scenario, selecting multiple assets, saving it, and confirming all selected assets remain associated and visible on subsequent review.

**Acceptance Scenarios**:

1. **Given** a threat model with multiple eligible assets, **When** an authorized user creates or edits a STRIDE scenario, **Then** they can select more than one asset for the scenario and must select at least one asset before saving.
2. **Given** a threat scenario with multiple selected assets, **When** the scenario is saved and reopened, **Then** the same asset membership remains associated with that scenario regardless of display order.

---

### User Story 2 - Assign multiple STRIDE-LM categories to a threat scenario (Priority: P2)

An assessment manager can assign more than one STRIDE-LM category to a STRIDE threat scenario when the scenario spans multiple classification dimensions and should not be forced into a single category, while non-STRIDE methodologies keep their current categorization behavior.

**Why this priority**: A single-category model can understate the scope of a scenario and makes reporting less accurate when the same scenario fits multiple STRIDE-LM categories.

**Independent Test**: Can be fully tested by assigning multiple STRIDE-LM categories to a threat scenario, saving it, and confirming the scenario and related views retain and display each assigned category.

**Acceptance Scenarios**:

1. **Given** a threat scenario that legitimately fits more than one STRIDE-LM category, **When** an authorized user edits the scenario, **Then** they can select all applicable categories without creating duplicate scenarios and must select at least one STRIDE-LM category before saving.
2. **Given** a threat scenario with multiple STRIDE-LM categories, **When** the scenario is viewed in the threat detail view, threat dashboard or model summary, or threat CSV or HTML/PDF exports, **Then** all assigned categories are shown consistently.

---

### User Story 3 - Review multi-assigned scenarios clearly (Priority: P3)

A reviewer needs to understand which assets and STRIDE-LM categories apply to a threat scenario without reconstructing that context from duplicate entries or external notes.

**Why this priority**: Reviewers rely on threat scenarios for analysis and reporting. If multiple assignments are hard to interpret, the feature adds complexity instead of clarity.

**Independent Test**: Can be fully tested by reviewing scenario detail and summary views and confirming multi-assigned assets and STRIDE-LM categories are easy to identify without ambiguity.

**Acceptance Scenarios**:

1. **Given** a threat scenario with multiple assets and STRIDE-LM categories, **When** a reviewer opens the scenario, **Then** each assignment is clearly visible and distinguishable.
2. **Given** a threat dashboard, model summary, or threat CSV or HTML/PDF export containing multi-assigned scenarios, **When** a reviewer scans the output, **Then** they can tell which assets and STRIDE-LM categories belong to each scenario without losing context.

---

### User Story 4 - Attach multiple ticket links to a risk (Priority: P3)

An assessment manager can associate multiple ticket links with a single risk, with each link storing a short label and a URL so remediation work tracked across one or more external work items remains visible from the risk workspace.

**Why this priority**: Risk treatment often spans multiple tickets. Restricting a risk to one linked ticket forces users to store incomplete remediation context or move that context outside the system.

**Independent Test**: Can be fully tested by editing a risk, adding multiple labeled ticket links, saving it, and confirming each link remains available during later review.

**Constraint**: Risks may be saved with zero, one, or many ticket links.

**Label Rule**: Each ticket-link label must be 1 to 80 characters long.

**Acceptance Scenarios**:

1. **Given** a risk that requires multiple remediation work items, **When** an authorized user edits the risk, **Then** they can add more than one labeled ticket link to that risk.
2. **Given** a risk with multiple ticket links, **When** the risk is viewed in the risk detail or edit review surface, the risk dashboard, or risk API output, **Then** all saved labels and URLs are displayed consistently for review.

---

### Edge Cases

- If a previously saved asset becomes archived, deleted, or unavailable for new scenarios, it remains visible on the existing scenario as a read-only historical association until a user removes it, and it cannot be newly selected or re-selected.
- If a previously saved STRIDE-LM category becomes unavailable for new scenarios, it remains visible on the existing scenario as a read-only historical association until a user removes it, and it cannot be newly selected or re-selected.
- If an existing single-assignment scenario is opened and saved without multiselect changes, it remains valid and is saved successfully as the equivalent single-item plural associations without forcing reassignment.
- When a scenario has many selected assets or STRIDE-LM categories, interactive views show a shortened inline summary with access to the full list, while CSV and HTML/PDF exports always include the full list.
- If a saved ticket link later becomes malformed, removed, or unreachable, the risk continues to preserve the saved label and URL for review, flags the link as invalid or unreachable when that can be detected, and allows the user to edit or remove it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow authorized users to assign multiple assets to a single STRIDE threat scenario and MUST require at least one asset before the scenario can be saved.
- **FR-002**: The system MUST allow authorized users to assign multiple STRIDE-LM categories to a single STRIDE threat scenario and MUST require at least one STRIDE-LM category before a STRIDE scenario can be saved.
- **FR-003**: The system MUST preserve all selected assets and STRIDE-LM categories when a threat scenario is created, edited, viewed, exported, or reopened for further editing.
- **FR-004**: The system MUST continue to support existing threat scenarios that currently have only one asset or one STRIDE-LM category without requiring immediate rework by users, and MUST keep deprecated compatibility aliases in threat exports and the risk API for one release cycle.
- **FR-004A**: The system MUST preserve existing single-assignment scenarios during ordinary edits and save them successfully as equivalent single-item plural associations when users make no multiselect changes.
- **FR-005**: The system MUST clearly display all assigned assets and STRIDE-LM categories in the threat detail view, threat dashboard or model summary, and threat CSV and HTML/PDF exports so users do not need to infer hidden assignments.
- **FR-005A**: Interactive threat review surfaces MUST remain readable when scenarios have many assigned assets or STRIDE-LM categories by showing a shortened inline summary with access to the full list, while CSV and HTML/PDF exports MUST include the full list.
- **FR-006**: The system MUST prevent invalid, duplicate, or no-longer-available selections from being newly stored as part of a threat scenario update, while preserving historically valid but now-unavailable asset and STRIDE-LM category associations as read-only until a user removes them.
- **FR-007**: The system MUST record who made each multi-assignment update and when it occurred, including separate audit visibility for asset additions or removals, STRIDE-LM category additions or removals, and risk ticket-link additions, removals, or edits.
- **FR-008**: The system MUST enforce existing role-based permissions so that only users with edit permission may create or change threat scenario assignment details or risk ticket links, while authorized reviewers may view them in read-only form.
- **FR-009**: The system MUST preserve reporting and review workflows for scenarios with multiple assets and STRIDE-LM categories across the threat detail view, threat dashboard or model summary, and threat CSV and HTML/PDF exports.
- **FR-010**: The system MUST allow authorized users to associate multiple ticket links with a single risk, and risks MUST remain valid when no ticket links are provided.
- **FR-011**: The system MUST store a label of 1 to 80 characters and a URL for each ticket link associated with a risk.
- **FR-012**: The system MUST preserve all saved ticket links when a risk is created, edited, viewed, or reopened for further editing.
- **FR-013**: The system MUST prevent invalid ticket links from being newly stored, MUST reject duplicate ticket links for the same risk when both the label and URL match an existing saved link, and MUST preserve previously saved ticket links for review while flagging malformed or unreachable links when that can be detected.
- **FR-014**: The system MUST clearly display each ticket link's label and URL in the risk detail or edit review surface, the risk dashboard, and risk API output.

### Key Entities *(include if feature involves data)*

- **Threat Scenario**: A documented threat analysis item that can be associated with multiple assets and multiple STRIDE-LM categories.
- **Threat Asset Assignment**: A stored relationship between a threat scenario and one selected asset in the threat model scope.
- **Threat Category Assignment**: A stored relationship between a threat scenario and one selected STRIDE-LM category used to classify the scenario.
- **Risk Ticket Link**: A stored reference from a risk record to one external remediation or tracking ticket, including a short label and URL.
- **Update Audit Event**: A time-stamped record of a user action that changed a threat scenario's asset or STRIDE-LM category assignments, or a risk's ticket links.

## Security, Audit, and Operations *(mandatory)*

- **Authorization Impact**: Multi-assignment and ticket-link editing are limited to users who already have threat or risk management edit permission; authorized reviewers may have read-only visibility into asset selections, STRIDE-LM category selections, and ticket links.
- **Audit/Event Impact**: Every create or update that changes asset assignments, STRIDE-LM category assignments, or a risk's ticket links must record actor, timestamp, affected record, and the type of change performed.
- **Data Sensitivity Impact**: Asset selections and STRIDE-LM category assignments can reveal sensitive system scope and security context and must follow existing access and retention controls.
- **Migration/Backfill Impact**: Existing single-assignment scenarios may require data migration, and deprecated compatibility aliases in threat exports and the risk API must remain available for one release cycle so legacy consumers remain valid during transition.
- **Localization Impact**: New selection labels, ticket-link labels, validation messages, and display text will require translation support.
- **Deployment/Configuration Impact**: Release planning must include checks that existing scenario forms, lists, and exports still behave correctly after multiselect support is introduced.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can save a threat scenario with more than one asset and more than one STRIDE-LM category without creating duplicate scenarios.
- **SC-002**: Reviewers can identify all assigned assets and STRIDE-LM categories for a scenario in under 30 seconds on the threat detail view and threat dashboard or model summary view, and the same assignments remain unambiguous in threat CSV and HTML/PDF exports.
- **SC-003**: 100% of threat assignment changes and risk ticket-link changes include an attributable audit history showing actor, timestamp, and affected record.
- **SC-004**: Existing single-assignment threat scenarios remain viewable and editable after the feature is introduced.
- **SC-005**: Users can save and later review more than one labeled ticket link on a single risk without losing previously entered links.

## Assumptions

- The primary scope of this feature is the threat modeling workflow rather than broader risk synchronization behavior.
- Existing threat scenarios may currently allow only one asset and one STRIDE-LM category, and users need backward-compatible support as multiselect is introduced.
- PASTA, LINDDUN, and OWASP scenarios keep their existing single-category behavior in this feature.
- Reviewers need visibility into multi-assigned assets and STRIDE-LM categories, but they do not necessarily need permission to edit them.
- Existing audit, retention, export, and translation practices will be reused for any new assignment controls or risk ticket-link display text.