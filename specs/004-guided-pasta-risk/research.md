# Research: Guided PASTA Risk Analysis

## Decision 1: Extend the current model-level PASTA implementation instead of designing a second workflow layer

- Decision: Build the guided risk-analysis extension on top of the already implemented `ThreatModel` + `PastaStageRecord` + `PastaFinding` model-level PASTA workflow in `scaffold/apps/threat/`.
- Rationale: The repository already contains model-level PASTA persistence, stage gating, methodology-aware exports, and PASTA-specific templates. Reusing those surfaces keeps the feature aligned with the existing threat domain and avoids reopening settled design choices from feature 003.
- Alternatives considered:
  - Reintroduce PASTA as scenario-centric risk records: rejected because the current code has already moved PASTA to model-level stages and findings.
  - Create a separate guided PASTA module: rejected because threat ownership, permissions, bootstrap logic, exports, and downstream sync already live in the threat module.

## Decision 2: Represent structured stage-seven risk scoring with a dedicated conclusion extension, not generic fields on every finding

- Decision: Keep `PastaFinding` as the shared narrative artifact and add a dedicated one-to-one structured extension for stage-seven `risk_conclusion` findings that stores likelihood, impact, publish metadata, and linked risk-workspace projection state.
- Rationale: The current `PastaFinding` model is intentionally generic across seven stages. Stage seven now needs structured scoring, publication metadata, and source-of-truth linkage that do not apply to stage-one objectives or stage-five vulnerabilities. A focused extension keeps validation precise and the migration narrowly scoped.
- Alternatives considered:
  - Add risk scoring and publication columns directly to `PastaFinding`: rejected because it would add many nullable stage-seven-only fields to every finding row.
  - Flatten stage-seven outcomes into `ThreatScenario`: rejected because the clarified workflow keeps PASTA as the authoritative source after publication.

## Decision 3: Publish risk conclusions explicitly from the threat module and make republish idempotent

- Decision: Add explicit publish and republish actions on eligible stage-seven conclusions in the threat module, creating or refreshing one linked risk-workspace record per conclusion.
- Rationale: The clarified spec rejects automatic sync and requires users to decide when a conclusion is mature enough to enter the risk workspace. Explicit publication also fits the current threat-to-risk pattern, where scenario sync already happens through service helpers and dedicated routes.
- Alternatives considered:
  - Auto-sync every eligible stage-seven change into risk: rejected because the user chose explicit publication.
  - Create a one-time snapshot with no refresh path: rejected because the user also wants the linked risk to stay aligned through deliberate republish.

## Decision 4: Keep PASTA as the source of truth and treat the risk workspace record as a projection

- Decision: Store the linkage on the PASTA side and treat the downstream `Risk` row as a published projection refreshed from the PASTA conclusion rather than a second authoritative record.
- Rationale: The clarified source-of-truth rule means the risk workspace must remain navigable and useful without becoming the master for PASTA-specific scoring, revalidation, and traceability. This mirrors the existing scenario-to-risk sync pattern while avoiding split-brain edits.
- Alternatives considered:
  - Let the risk workspace become authoritative after publication: rejected because it breaks the clarified ownership model.
  - Allow both sides to edit the same authoritative fields freely: rejected because it creates ambiguous reconciliation rules.

## Decision 5: Reuse the existing risk workspace chance, impact, and severity logic instead of introducing a second scoring model

- Decision: Map PASTA stage-seven likelihood and impact values to the existing 1-5 threat and risk scoring semantics, then derive overall score and severity through the same risk-workspace weight and threshold model already used for `Risk`.
- Rationale: The spec explicitly asks for scoring similar to STRIDE functionality. The codebase already has `_CHANCE_MAP`, `_IMPACT_MAP`, and `RiskSeverityThreshold` handling, so reusing that logic preserves comparability between STRIDE-derived and PASTA-derived risks.
- Alternatives considered:
  - Create a PASTA-only risk matrix or scale: rejected because it would reduce cross-workspace comparability.
  - Store only qualitative text in stage seven and leave scoring to risk publication time: rejected because the user wants likelihood and impact as part of the PASTA experience itself.

## Decision 6: Gate publication on structured completeness and currentness, not on a new approval workflow

- Decision: A stage-seven conclusion becomes publishable only when it has likelihood, impact, an overall risk outcome narrative, and no active revalidation flag.
- Rationale: The clarified spec resolves publication readiness around completeness and currentness, not around a new reviewer approval state. This keeps v1 aligned with existing edit/save flows while preventing stale conclusions from entering the risk workspace.
- Alternatives considered:
  - Allow publication whenever any score exists: rejected because it conflicts with the explicit gating choice.
  - Add a separate approval workflow: rejected because the user chose not to add that complexity in v1.

## Decision 7: Reuse the existing interactive, HTML, PDF, and CSV reporting surfaces and extend their PASTA-specific content

- Decision: Keep the current threat-model review and export routes and expand the PASTA-specific rendering to show stage-seven scores, publish state, and risk-workspace linkage.
- Rationale: The codebase already has `pasta_export_report.html`, methodology-aware branching in the export routes, and CSV export branching for PASTA. Extending these surfaces satisfies the clarified v1 reporting scope without introducing a new reporting subsystem.
- Alternatives considered:
  - Restrict v1 reporting to the interactive UI: rejected because the user chose UI plus HTML, PDF, and CSV.
  - Build a separate risk-style report template outside the threat module: rejected because the current export routes already branch by methodology.