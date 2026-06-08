# Contract: Threat Export Surfaces for PASTA

## Scope

This contract defines how the existing threat export surfaces should behave for PASTA models in v1 while preserving current behavior for non-PASTA models.

## Non-PASTA compatibility

- STRIDE-LM and other current non-PASTA model exports remain backward-compatible unless explicitly extended for shared terminology.
- Existing filename patterns and export route paths remain unchanged.

## HTML export

### Surface

- `GET /threat/<model_id>/export/html`

### PASTA behavior

- Cover section includes model title, methodology, owner, generated date, and scope.
- Summary section includes:
  - overall workflow state
  - stage completion counts
  - number of findings
  - number of downstream linked/generated threat scenarios
- Stage sections render in canonical order and include:
  - stage name
  - stage status
  - stage summary text
  - findings captured for the stage
  - optional STRIDE-LM mappings for findings where present
- A downstream scenario appendix lists linked/generated standard threat scenarios without implying that all PASTA findings are scenarios.

## PDF export

### Surface

- `GET /threat/<model_id>/export/pdf`

### PASTA behavior

- Mirrors HTML export content and ordering.
- Uses the same methodology-aware rendering rules as HTML before PDF conversion.

## CSV export

### Surface

- `GET /threat/<model_id>/export/csv`

### PASTA behavior

- CSV exports one row per PASTA finding.
- Required columns:
  - `model_id`
  - `model_title`
  - `methodology`
  - `stage_code`
  - `stage_name`
  - `stage_status`
  - `finding_id`
  - `finding_type`
  - `finding_title`
  - `asset_names`
  - `stride_mappings`
  - `linked_scenario_ids`
  - `linked_scenario_titles`
  - `finding_status`
- Optional columns may include priority, evidence summary, or residual risk indicators if implementation stores them for the finding type.

## Export terminology and traceability rules

- PASTA-native stage content must not be mislabeled as STRIDE categories or standard threat scenarios.
- Reused STRIDE-LM classifications must appear as mappings or supporting classifications, not as the primary workflow grouping.
- Linked/generated downstream scenarios must remain traceable to their source PASTA findings in all export surfaces where scenario references appear.

## Feasibility boundary for v1

- HTML and PDF exports are expected to provide the full methodology-aware review output.
- CSV export is expected to provide structured, flat finding rows rather than reproduce the full narrative layout.
- No separate PASTA-only export route is introduced in v1.
