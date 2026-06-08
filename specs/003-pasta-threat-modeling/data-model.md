# Data Model: PASTA Threat Modeling

## ThreatModel (extended)

Represents the top-level threat-model container and becomes the owning record for a full PASTA workflow.

### New or Changed Fields

- `methodology`: string/enum value for the model's primary methodology (`STRIDE`, `PASTA`, `LINDDUN`, `OWASP`)
- `bootstrap_source_model_id`: nullable self-referential foreign key to the source STRIDE-LM model when the model was created through one-way bootstrap
- `current_workflow_state`: optional derived or persisted summary state such as `draft`, `in_progress`, `needs_revalidation`, `completed`

### Relationships

- One-to-many with `ThreatModelAsset` (existing)
- One-to-many with `ThreatScenario` (existing)
- One-to-many with `PastaStageRecord` when `methodology == "PASTA"`
- Optional self-reference to the STRIDE-LM source model used for bootstrap

### Validation Rules

- PASTA models must initialize exactly seven stage records using the canonical stage codes.
- Non-PASTA models must not require PASTA stage records.
- Bootstrap source, when present, must refer to an existing non-archived threat model that the current user may review.

## PastaStageRecord

Represents one of the seven ordered PASTA stages for a PASTA threat model.

### Fields

- `id`
- `threat_model_id`
- `stage_code`: enum/string (`define_objectives`, `define_technical_scope`, `decompose_application`, `analyze_threats`, `vulnerability_analysis`, `attack_analysis`, `risk_impact_analysis`)
- `display_order`: integer 1..7
- `status`: enum/string (`locked`, `available`, `completed`, `needs_revalidation`)
- `summary`: long-form stage overview text
- `completion_notes`: optional reviewer-facing note about what satisfied the gate
- `completed_at`
- `completed_by_id`
- `last_revalidated_at`

### Relationships

- Many-to-one with `ThreatModel`
- One-to-many with `PastaFinding`
- Optional many-to-one with `User` for `completed_by_id`

### Validation Rules

- Unique pair on `threat_model_id + stage_code`
- `display_order` must match the canonical stage ordering
- Stage 1 starts as `available`; later stages cannot become `available` until the immediately preceding stage meets the minimum gate
- Editing an earlier completed stage may force later stages into `needs_revalidation`

### State Transitions

- `locked -> available`
- `available -> completed`
- `completed -> needs_revalidation`
- `needs_revalidation -> completed`

## PastaFinding

Represents a reviewable finding captured within one PASTA stage.

### Fields

- `id`
- `stage_record_id`
- `finding_type`: enum/string such as `objective`, `scope_item`, `decomposition_item`, `threat`, `vulnerability`, `attack_path`, `risk_conclusion`
- `title`
- `description`
- `evidence`
- `priority`: optional severity/importance indicator for later-stage findings
- `status`: enum/string (`draft`, `current`, `needs_revalidation`, `archived`)
- `source_library_entry_id`: nullable FK to `ThreatLibraryEntry`
- `created_by_id`
- `updated_by_id`

### Relationships

- Many-to-one with `PastaStageRecord`
- Optional many-to-one with `ThreatLibraryEntry`
- Many-to-many with `ThreatModelAsset` through `PastaFindingAssetLink`
- One-to-many with `PastaFindingStrideCategoryLink`
- One-to-many with `PastaFindingThreatScenarioLink`

### Validation Rules

- Every finding must belong to exactly one stage record
- Findings in stages 4-7 may omit STRIDE-LM mappings; stages 1-3 should not require them
- `finding_type` must align with the stage family that owns the record
- Downstream scenario generation/linking is allowed only for findings whose type is operationally threat-oriented (`threat`, `vulnerability`, `attack_path`, or `risk_conclusion` when implementation chooses to support it)

## PastaFindingAssetLink

Associates a PASTA finding with one or more existing threat-model assets.

### Fields

- `finding_id`
- `asset_id`

### Relationships

- Many-to-one with `PastaFinding`
- Many-to-one with `ThreatModelAsset`

### Validation Rules

- Unique pair on `finding_id + asset_id`
- Asset must belong to the same `ThreatModel` as the owning stage record

## PastaFindingStrideCategoryLink

Associates one PASTA finding with one STRIDE-LM category when the methodologies overlap.

### Fields

- `id`
- `finding_id`
- `stride_category`: string/enum value from the existing `StrideCategory`

### Relationships

- Many-to-one with `PastaFinding`

### Validation Rules

- Unique pair on `finding_id + stride_category`
- Only valid `StrideCategory` values may be stored
- Absence of rows is valid and must not block saving a PASTA finding

## PastaFindingThreatScenarioLink

Provides traceability between a PASTA finding and a standard threat scenario used in downstream workflows.

### Fields

- `id`
- `finding_id`
- `threat_scenario_id`
- `link_type`: enum/string (`generated`, `linked_existing`)
- `created_at`
- `created_by_id`

### Relationships

- Many-to-one with `PastaFinding`
- Many-to-one with `ThreatScenario`
- Optional many-to-one with `User`

### Validation Rules

- Unique pair on `finding_id + threat_scenario_id`
- Linked or generated scenario must belong to the same `ThreatModel` as the PASTA finding's parent model
- Deleting a PASTA finding must preserve or explicitly reconcile downstream scenario traceability according to implementation rules; no silent orphaning

## ThreatScenario (existing, reused)

Continues to represent the standard downstream threat record used by current risk sync, SSP sync, and scenario-centric exports.

### Relevant Impact

- Scenario creation remains supported directly through current threat routes for non-PASTA workflows.
- PASTA-driven downstream integration reuses `ThreatScenario` rather than replacing it.
- Existing per-scenario `methodology` and `pasta_stage` fields need migration-time review: either deprecate them in favor of model-level PASTA state or retain them only for backward-compatible reads while new PASTA workflow data lives in the new stage/finding tables.

## Derived Views and Workflow Rules

- A PASTA model is considered `completed` only when all seven stage records are `completed` and no later stage remains `needs_revalidation`.
- Stage unlock rules are based on minimum required content, which should be implemented as service-level validation per stage rather than as free-form UI checks.
- Export projections must distinguish between:
  - stage summaries
  - PASTA findings
  - optional STRIDE-LM mappings
  - downstream linked/generated standard threat scenarios
