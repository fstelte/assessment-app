# Research: PASTA Threat Modeling

## Decision 1: Make PASTA a model-level workflow, not a scenario-level toggle

- Decision: Treat PASTA as a property of `ThreatModel` and persist its workflow through model-owned stage and finding records.
- Rationale: The existing threat module already centers navigation, review, exports, and audit events on `ThreatModel`. The current `ThreatScenario.methodology` and `pasta_stage` fields are sufficient for tagging individual scenarios, but they cannot represent a seven-stage, partially completed, resumable process with gating and revalidation.
- Alternatives considered:
  - Keep using per-scenario `methodology` and `pasta_stage`: rejected because it fragments one PASTA analysis across unrelated scenario rows and does not model stage progression.
  - Build a separate PASTA module outside `scaffold/apps/threat/`: rejected because it would duplicate assets, exports, permissions, and downstream risk/threat integration already owned by the threat module.

## Decision 2: Use the canonical seven PASTA stages for workflow state

- Decision: Use these canonical stage codes for workflow and persistence: `define_objectives`, `define_technical_scope`, `decompose_application`, `analyze_threats`, `vulnerability_analysis`, `attack_analysis`, and `risk_impact_analysis`.
- Rationale: The feature spec and the referenced PASTA source both define the workflow around those seven stages. The current seed library includes PASTA-oriented category labels such as `Asset Analysis` and `Attack Modeling`, but those are better treated as library-entry hints than as the authoritative workflow taxonomy.
- Alternatives considered:
  - Reuse the current `pasta_stage` dropdown values directly: rejected because they do not match the clarified workflow and would make exports and review terminology inconsistent.
  - Store only numeric stage order without explicit codes: rejected because descriptive codes are easier to localize, audit, and render consistently.

## Decision 3: Persist stage status explicitly to support light gating and revalidation

- Decision: Give each stage record an explicit status such as `locked`, `available`, `completed`, or `needs_revalidation`, with stage 1 available on creation and later stages unlocked only after the preceding stage meets minimum content rules.
- Rationale: The clarified behavior requires ordered progression, editable earlier stages, and visible revalidation when upstream analysis changes. Explicit status is simpler to audit and render than inferring every state from ad hoc content checks at display time.
- Alternatives considered:
  - Infer stage availability from whether any text exists in prior stages: rejected because it is too brittle for auditability and revalidation messaging.
  - Force a strict wizard with irreversible progression: rejected because the clarified workflow intentionally keeps earlier stages editable.

## Decision 4: Reuse STRIDE-LM at the finding level, not at the stage level

- Decision: Allow zero-to-many STRIDE-LM mappings on individual PASTA findings rather than on the PASTA model or entire stage.
- Rationale: The feature explicitly says PASTA should use STRIDE-LM where possible, but not everywhere. Finding-level mapping lets stage 4-6 threat analysis reuse current STRIDE-LM categories without forcing classification on business-objective or scope artifacts.
- Alternatives considered:
  - Require a STRIDE-LM mapping for every PASTA finding: rejected because many PASTA artifacts are not threat-category classifications.
  - Map STRIDE-LM once per model: rejected because overlap varies by finding, not by entire model.

## Decision 5: Use one-way bootstrap from existing STRIDE-LM models into new PASTA models

- Decision: Support a one-way bootstrap flow that creates a new PASTA model from an existing STRIDE-LM model and records the source model reference.
- Rationale: The clarified workflow wants reuse without converting one record into a dual-mode object. A new PASTA model can inherit context, assets, and potentially candidate scenarios while preserving the source STRIDE-LM record as historical evidence.
- Alternatives considered:
  - In-place methodology switching on a single model: rejected because it creates ambiguous ownership of stage records, exports, and downstream scenario relationships.
  - No conversion support: rejected because it discards too much current threat-model value and weakens the requested extension-to-STRIDE story.

## Decision 6: Let selected PASTA threat findings generate or link standard threat scenarios

- Decision: Keep PASTA stage/finding records distinct, and allow authorized users to generate or link standard `ThreatScenario` rows from selected threat findings only when downstream sync, mitigation, or export flows need them.
- Rationale: The threat module already syncs standard scenarios to risk and SSP workflows. Selective linking preserves that investment while avoiding automatic flattening of every PASTA artifact into the scenario schema.
- Alternatives considered:
  - Auto-generate standard scenarios for every stage 4-6 finding: rejected because it would create noisy duplicate records and blur methodology boundaries.
  - Make PASTA review-only with manual downstream re-entry: rejected because it breaks traceability and adds avoidable operator work.

## Decision 7: Extend existing threat review/export surfaces rather than creating a separate reporting subsystem

- Decision: Reuse `model_detail` and the existing HTML/PDF/CSV export routes for PASTA-aware review outputs, with methodology-specific rendering rules.
- Rationale: Current review/export paths are already model-centric and audited. Extending them preserves familiar user entry points and keeps v1 within the repo's existing threat reporting architecture.
- Alternatives considered:
  - PASTA only in interactive UI: rejected because the spec requires existing export surfaces where feasible.
  - A completely separate PASTA reporting engine: rejected because it adds avoidable UI and maintenance complexity for v1.

## Decision 8: Keep threat library PASTA entries as optional accelerators, not the source of truth for stage progression

- Decision: Existing PASTA entries in `scaffold/apps/threat/data/library.json` remain optional prompts or seed inputs for findings, but stage progression and completion are driven by the explicit PASTA stage model.
- Rationale: The library is valuable for bootstrapping analysis, but it is not a substitute for stage state, gating, audit events, or review completeness.
- Alternatives considered:
  - Derive stage completion solely from imported library entries: rejected because users must be able to perform manual and organization-specific analysis.
  - Ignore the library entirely for PASTA: rejected because the repo already ships curated PASTA-oriented content that should remain useful.
