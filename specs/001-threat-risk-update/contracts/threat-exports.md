# Threat Export Contract Updates

## Affected Interface

- `GET /threat/<model_id>/export/csv`
- `GET /threat/<model_id>/export/html`
- `GET /threat/<model_id>/export/pdf`

## CSV Contract

The CSV export remains one row per threat scenario.

### Existing scalar columns kept for compatibility

- `asset`: derived from the first selected asset, or empty when none are selected
- `stride_category`: derived from the first selected STRIDE-LM category, or empty when none are selected

### New plural columns

- `assets`: pipe-delimited ordered asset names, for example `API Gateway | Payroll Portal`
- `stride_categories`: pipe-delimited ordered STRIDE-LM values, for example `spoofing | elevation_of_privilege`

### Unchanged columns

- `id`
- `title`
- `likelihood`
- `impact_score`
- `risk_score`
- `risk_level`
- `treatment`
- `status`
- `mitigation`
- `owner`

## HTML/PDF Contract

Scenario detail sections, summary cards, and category groupings must render all assigned assets and STRIDE-LM categories without collapsing them into a single label.

## Review Rules

- Review views must preserve scenario readability when many assets or categories are selected
- Exported terminology must match the interactive UI
- Compatibility aliases should be documented as transitional and removable in a later cleanup release