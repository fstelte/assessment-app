# Data Model: Guided PASTA Risk Analysis

## ThreatModel (existing, reused)

Represents the owning threat-model record and continues to be the top-level container for the guided PASTA workflow.

### Relevant Existing Fields and Relationships

- `methodology`
- `bootstrap_source_model_id`
- `pasta_stages`
- `assets`
- `scenarios`

### Relevant Impact

- Guided PASTA remains model-level and does not create a second top-level entity.
- Publication eligibility is derived from stage-seven findings and the model's downstream revalidation state, not from a new top-level approval field.

## PastaStageRecord (existing, reused)

Represents one of the seven canonical PASTA stages.

### Relevant Existing Fields

- `stage_code`
- `display_order`
- `status`
- `summary`
- `completion_notes`
- `completed_at`
- `last_revalidated_at`

### Relevant Impact

- Stage seven remains `risk_impact_analysis`.
- Publication readiness is blocked whenever the owning stage or later guided state is in `needs_revalidation`.
- Stage summary and stage status remain the main workflow-level review signals in UI and exports.

## PastaFinding (existing, reused)

Represents a narrative, reviewable artifact captured inside one PASTA stage.

### Relevant Existing Fields

- `stage_record_id`
- `finding_type`
- `title`
- `description`
- `evidence`
- `priority`
- `status`
- `asset_links`
- `stride_links`
- `scenario_links`

### Relevant Impact

- Stage-seven risk outcomes continue to use `finding_type = risk_conclusion` as the narrative anchor.
- The finding remains the review and export entry point for narrative risk analysis, supporting evidence, mapped assets, and optional STRIDE context.
- A risk conclusion finding may exist in draft/current/revalidation states even when no downstream risk has been published yet.

## PastaRiskConclusion (new)

Represents the structured stage-seven scoring and publication state for one `PastaFinding` whose type is `risk_conclusion`.

### Fields

- `id`
- `finding_id` (unique foreign key to `pasta_findings.id`)
- `likelihood_score` (integer 1..5)
- `impact_score` (integer 1..5)
- `overall_score` (derived or cached integer based on the current risk formula)
- `treatment` (string/enum aligned with `RiskTreatmentOption`, defaulting to `mitigate` in v1)
- `published_risk_id` (nullable foreign key to `risk_items.id`, unique when present)
- `last_published_at`
- `last_published_by_id`
- `publication_notes` (optional explanatory note shown in the source workflow)

### Relationships

- One-to-one with `PastaFinding`
- Optional many-to-one with `Risk`
- Optional many-to-one with `User` for the last publisher

### Validation Rules

- The parent finding must belong to a `PastaStageRecord` whose `stage_code` is `risk_impact_analysis`.
- The parent finding must have `finding_type = risk_conclusion`.
- `likelihood_score` and `impact_score` must remain within 1..5.
- `published_risk_id` may be set only when the parent finding is current and the owning stage is not marked for revalidation.
- Each risk conclusion can link to at most one published risk-workspace record at a time.

### State/Workflow Rules

- A conclusion is publishable only when it has likelihood, impact, an overall risk outcome in the parent finding narrative, and no active revalidation flag.
- Republishing updates the linked risk record referenced by `published_risk_id`; it does not create a second linked risk.
- If upstream stage changes trigger revalidation, the conclusion remains reviewable but becomes non-publishable until it is current again.

## Risk (existing, reused as projection)

Represents the downstream risk-workspace record that PASTA may publish into.

### Relevant Existing Fields

- `title`
- `description`
- `impact`
- `chance`
- `treatment`
- `components`
- `controls`
- `closed_at`

### Relevant Impact

- Published PASTA conclusions create or refresh `Risk` rows using existing risk-workspace semantics.
- `chance` and `impact` values are mapped from the PASTA 1-5 scores into `RiskChance` and `RiskImpact`.
- The risk record remains a projection of the PASTA conclusion rather than the master for stage-seven scoring.

## Risk Workspace Link (derived relationship)

Represents the traceable connection between a structured PASTA risk conclusion and its downstream risk-workspace record.

### Storage Strategy

- The link is stored on `PastaRiskConclusion.published_risk_id`.
- Reverse navigation from risk to source is resolved by querying the conclusion table by `published_risk_id`.

### Validation Rules

- `published_risk_id` must reference an existing `Risk` row.
- The same risk row must not be linked to multiple PASTA conclusions.
- If the linked risk row is closed or manually changed in a way that diverges from the source, the PASTA side still remains authoritative and the next republish reconciles the projection.

## Derived Rules and Mapping Logic

- `overall_score` uses the same weighted product semantics as the current risk workspace: likelihood weight x impact weight.
- Overall priority/severity displayed in guided PASTA and reports is derived from the current `RiskSeverityThreshold` configuration or the same threshold service used by the risk workspace.
- Components published into the risk workspace are derived from the conclusion's linked assets or the model's context scope using the same matching pattern already used by scenario-to-risk sync.
- Publication does not require a separate approval entity in v1; authorization is inherited from the source PASTA model's edit permission.