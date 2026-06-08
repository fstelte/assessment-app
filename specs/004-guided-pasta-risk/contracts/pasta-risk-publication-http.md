# Contract: PASTA Risk Publication HTTP Surfaces

## Scope

This contract defines the expected HTTP behavior for stage-seven scoring, publish readiness, and explicit risk-workspace publication for guided PASTA models.

## Authorization Baseline

- Review routes continue to require the current threat review permission path.
- Stage-seven mutation and publication routes follow the same threat edit permission path already used for PASTA stage edits.
- No separate publish-only role is introduced in v1.
- All publish and republish actions emit audit events.

## 1. Review a PASTA model with stage-seven conclusions

### Route

- `GET /threat/<model_id>`

### Response expectations

- PASTA detail view continues to render ordered stage summaries and findings.
- Stage-seven `risk_conclusion` findings additionally show:
  - likelihood score
  - impact score
  - derived overall score or priority
  - publication state (`not_published`, `published`, `needs_revalidation` or equivalent UI state)
  - link to the published risk-workspace entry when present
- Conclusions blocked from publication show a clear reason, such as missing scores or active revalidation.

## 2. Edit stage-seven scoring

### Routes

- `GET /threat/<model_id>/pasta/findings/<finding_id>/risk`
- `POST /threat/<model_id>/pasta/findings/<finding_id>/risk`

### Request expectations

- `finding_id` must identify a PASTA finding belonging to the target model.
- The finding must belong to the `risk_impact_analysis` stage.
- POST payload includes structured likelihood and impact values and any additional treatment or publication note fields required by the source workflow.

### Response expectations

- Successful save updates the structured conclusion record while keeping the finding narrative intact.
- Revalidation state is recalculated after save.
- Audit event includes model ID, finding ID, and whether publication readiness changed.

## 3. Publish a PASTA conclusion to the risk workspace

### Route

- `POST /threat/<model_id>/pasta/findings/<finding_id>/publish-risk`

### Request expectations

- Caller must have permission to edit the source PASTA model.
- The conclusion must have likelihood, impact, an overall risk outcome narrative, and no active revalidation flag.
- The source PASTA conclusion remains authoritative; the route publishes a projection into the risk workspace.

### Response expectations

- On first publish, the route creates one linked risk-workspace record and stores the linkage on the PASTA conclusion.
- On republish, the route refreshes the existing linked risk rather than creating a duplicate.
- Success redirects back to the model detail or stage-seven view with a flash message and visible publish-state update.
- Blocked publication returns the user to the source workflow with a validation error explaining why the conclusion is not publishable.
- Audit event includes model ID, finding ID, risk ID, and whether the action created or refreshed the projection.

## 4. Display PASTA-published risks in the risk workspace

### Surfaces

- `GET /risk/`
- any existing risk detail or edit surface that already displays a linked threat source

### Response expectations

- A risk published from PASTA is visible through the existing risk workspace query path.
- The UI indicates the risk originated from a PASTA conclusion and links back to the source threat model and conclusion.
- Users may review the risk in the risk workspace without the workspace becoming the source of truth for the original PASTA conclusion.

## 5. Non-PASTA compatibility

- Existing `POST /threat/<model_id>/scenarios/<scenario_id>/sync-risk` behavior for standard threat scenarios remains unchanged.
- Existing risk-workspace bulk sync from threat scenarios remains unchanged.
- The new publication surfaces must not change route behavior for non-PASTA models.