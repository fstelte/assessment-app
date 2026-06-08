# Contract: Guided PASTA Reporting Surfaces

## Scope

This contract defines the required v1 reporting behavior for guided PASTA models across the interactive UI and the existing HTML, PDF, and CSV outputs.

## Supported v1 surfaces

- Interactive threat-model UI
- `GET /threat/<model_id>/export/html`
- `GET /threat/<model_id>/export/pdf`
- `GET /threat/<model_id>/export/csv`

## Non-PASTA compatibility

- Existing STRIDE and other non-PASTA reporting behavior remains backward-compatible.
- Existing route names, filenames, and general export flow remain unchanged.

## Interactive UI expectations

### Surface

- `GET /threat/<model_id>`

### Guided PASTA behavior

- Stage cards continue to render in canonical order.
- Stage-seven sections show:
  - risk conclusion title and narrative
  - likelihood score
  - impact score
  - derived overall score or priority
  - publication state
  - linked risk-workspace reference when published
- Draft or revalidation states are visually distinct from finalized current conclusions.

## HTML and PDF export expectations

### Surfaces

- `GET /threat/<model_id>/export/html`
- `GET /threat/<model_id>/export/pdf`

### Guided PASTA behavior

- Continue using the PASTA-specific export template path.
- Include a methodology-aware summary section with:
  - model title and methodology
  - overall stage completion status
  - number of risk conclusions
  - number of published risk-workspace links
- Stage-seven output includes the same semantic content as the interactive UI: narrative conclusion, scores, derived priority, and publication state.
- When a conclusion has been published, the export identifies the linked risk-workspace record without implying that the risk workspace is the source of truth.
- Revalidation or draft state is explicit in the export.

## CSV export expectations

### Surface

- `GET /threat/<model_id>/export/csv`

### Guided PASTA behavior

- Continue exporting one row per PASTA finding.
- Existing finding columns remain for non-stage-seven rows.
- Stage-seven rows add or populate these columns:
  - `likelihood_score`
  - `impact_score`
  - `overall_score`
  - `risk_priority`
  - `publication_state`
  - `published_risk_id`
- Non-stage-seven rows leave those columns blank.

## Terminology and style rules

- Reporting must preserve the same meaning and terminology as the interactive UI.
- PASTA-native conclusions must not be mislabeled as STRIDE scenarios or as standalone risk-workspace records.
- Publication state must communicate that the risk workspace entry is a linked projection of the PASTA conclusion.
- Styling and section structure should remain consistent with the existing threat and risk application surfaces.