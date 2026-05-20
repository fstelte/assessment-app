# Data Model: Threat Model and Risk Updates

## ThreatScenario

Represents one threat analysis record inside a threat model.

**Existing persisted fields kept**

- `id`
- `threat_model_id`
- `title`
- `description`
- `threat_actor`
- `attack_vector`
- `preconditions`
- `impact_description`
- `affected_cia`
- `likelihood`
- `impact_score`
- `risk_score`
- `risk_level`
- `treatment`
- `residual_likelihood`
- `residual_impact`
- `residual_risk_score`
- `residual_risk_level`
- `status`
- `owner_id`
- `library_entry_id`
- `methodology`
- `pasta_stage`
- `risk_id`

**Relationship changes**

- Replace singular `asset_id` usage with `assets[]`
- Replace singular `stride_category` usage with `stride_categories[]`
- Keep `controls[]` and `mitigation_actions[]` relationships unchanged

**Validation rules**

- STRIDE methodology scenarios must require one or more selected assets and one or more STRIDE-LM categories before save
- Selected asset IDs must belong to the owning threat model
- Duplicate asset/category links must not be persisted
- Threat asset and STRIDE-LM category relationships are stored as unordered membership; no sort order is persisted for threat relationships
- Existing single-value scenarios must remain editable after backfill

## ThreatScenarioAssetLink

Association row connecting one threat scenario to one threat model asset.

**Fields**

- `scenario_id` FK -> `threat_scenarios.id` (`CASCADE DELETE`)
- `asset_id` FK -> `threat_model_assets.id` (`CASCADE DELETE`)

**Constraints**

- Unique pair on `scenario_id + asset_id`

## ThreatScenarioStrideCategoryLink

Association row connecting one threat scenario to one STRIDE-LM category.

**Fields**

- `scenario_id` FK -> `threat_scenarios.id` (`CASCADE DELETE`)
- `stride_category` enum/string value from existing `StrideCategory`

**Constraints**

- Unique pair on `scenario_id + stride_category`

## Risk

Represents one tracked risk item.

**Existing persisted fields kept**

- `id`
- `title`
- `description`
- `discovered_on`
- `impact`
- `chance`
- `treatment`
- `treatment_plan`
- `treatment_due_date`
- `treatment_owner_id`
- `closed_at`

**Relationship changes**

- Replace scalar `ticket_url` usage with `ticket_links[]`
- Keep `components[]`, `controls[]`, and `impact_area_links[]` unchanged

**Validation rules**

- A risk may hold zero or more ticket links
- Each ticket link requires both `label` and `url`
- `label` must be 1 to 80 characters
- URLs must pass the same URL validation currently used for `ticket_url`
- Duplicate ticket links for the same risk must be rejected according to the selected uniqueness rule

## RiskTicketLink

Child row representing one external remediation or tracking reference for a risk.

**Fields**

- `id`
- `risk_id` FK -> `risk_items.id` (`CASCADE DELETE`)
- `label` string (1-80 chars, short reviewer-friendly text)
- `url` string (validated URL, max 500 chars)
- `sort_order` integer (preserves display/edit order)

**Constraints**

- Unique combination on `risk_id + label + url` to block duplicates per risk
- Cascade delete with parent risk

## Migration Notes

- Backfill each existing `ThreatScenario.asset_id` into one `ThreatScenarioAssetLink`
- Backfill each existing `ThreatScenario.stride_category` into one `ThreatScenarioStrideCategoryLink`
- Backfill each non-empty `Risk.ticket_url` into one `RiskTicketLink` with a default label and `sort_order = 0`
- After backfill, application code reads from the new relationships and only keeps deprecated single-value aliases in outward-facing contracts where needed