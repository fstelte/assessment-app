# Contract: PASTA Workflow HTTP Surfaces

## Scope

This contract defines the expected HTTP behavior for the model-level PASTA workflow inside the existing threat module. It documents route intent, authorization expectations, and request/response behavior for the planning and task-generation phases.

## Authorization Baseline

- Review routes require the existing threat review permission path (`login_required` plus current review access checks).
- Mutation routes require the existing threat edit permission path (admin or assessment manager).
- All mutation routes emit audit events for create/update/bootstrap/link actions.

## 1. Create PASTA model

### Route

- `GET /threat/new`
- `POST /threat/new`

### Request expectations

- Model create form includes a primary `methodology` choice.
- When `methodology=PASTA`, model creation initializes the seven canonical PASTA stage records.
- Optional bootstrap source selector is absent or disabled unless the user explicitly chooses a bootstrap flow.

### Response expectations

- Success redirects to the threat model detail/review surface for the newly created model.
- The initial stage state shows stage 1 available and later stages locked.
- Audit event includes model ID, methodology, and whether bootstrap was used.

## 2. Bootstrap PASTA from STRIDE-LM model

### Route

- `POST /threat/<source_model_id>/bootstrap-pasta`

### Request expectations

- Source model must be reviewable by the acting user.
- Bootstrap action creates a new `ThreatModel` with `methodology=PASTA`.
- Relevant source context may include title-derived metadata, scope, assets, and candidate scenario references, but bootstrap does not mutate the source model in place.

### Response expectations

- Success redirects to the new PASTA model.
- The new model stores traceability to the source model.
- Audit event includes source model ID and new model ID.

## 3. Review PASTA model

### Route

- `GET /threat/<model_id>`

### Response expectations

- For non-PASTA models, current STRIDE-LM-oriented behavior remains unchanged.
- For PASTA models, the detail view renders:
  - overall methodology and workflow status
  - ordered stage list with status badges
  - stage summaries and findings for completed or available stages
  - explicit markers for locked and `needs_revalidation` stages
  - linked/generated downstream threat scenarios where present
- Review output distinguishes PASTA-native findings from optional STRIDE-LM mappings.

## 4. Edit a PASTA stage

### Route

- `GET /threat/<model_id>/pasta/stages/<stage_code>`
- `POST /threat/<model_id>/pasta/stages/<stage_code>`

### Request expectations

- `stage_code` must be one of the canonical seven stages.
- User may edit an earlier stage even after later stages are unlocked.
- POST payload contains stage summary fields plus any stage-specific finding payload submitted through the form.

### Response expectations

- On success, the stage is re-evaluated against its minimum gate.
- If the gate is satisfied, the next stage becomes available.
- If upstream edits invalidate downstream assumptions, affected later stages become `needs_revalidation`.
- Audit event includes stage code, model ID, and whether stage status changed.

## 5. Manage PASTA findings

### Route

- `POST /threat/<model_id>/pasta/stages/<stage_code>/findings`
- `POST /threat/<model_id>/pasta/findings/<finding_id>/edit`
- `POST /threat/<model_id>/pasta/findings/<finding_id>/delete`

### Request expectations

- Finding payload supports finding type, narrative fields, optional asset links, optional library-entry source, and optional STRIDE-LM mappings.
- STRIDE-LM mappings are optional and validated only against existing STRIDE category values.

### Response expectations

- Stage review surface reflects the updated finding list.
- Audit history captures creation, update, and deletion with finding IDs.

## 6. Generate or link downstream threat scenario

### Route

- `POST /threat/<model_id>/pasta/findings/<finding_id>/generate-scenario`
- `POST /threat/<model_id>/pasta/findings/<finding_id>/link-scenario`

### Request expectations

- Only threat-oriented findings are eligible.
- Generate action creates a standard `ThreatScenario` in the same `ThreatModel`.
- Link action attaches an existing `ThreatScenario` from the same `ThreatModel`.

### Response expectations

- Traceability link is persisted between the PASTA finding and the target scenario.
- Review surfaces show the linked/generated scenario relationship.
- Audit event includes model ID, finding ID, target scenario ID, and link type.

## 7. Export PASTA model

### Routes

- `GET /threat/<model_id>/export/csv`
- `GET /threat/<model_id>/export/html`
- `GET /threat/<model_id>/export/pdf`

### Response expectations

- Existing export route names remain unchanged.
- Export payload branches by model methodology.
- PASTA export semantics are defined in `contracts/threat-exports.md`.
- Audit event continues using the existing threat-model export event family.
