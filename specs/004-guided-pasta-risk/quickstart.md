# Quickstart: Guided PASTA Risk Analysis

## Goal

Validate the guided stage-seven scoring, explicit publish flow, and reporting updates for PASTA models without regressing current PASTA or STRIDE behavior.

## Prerequisites

- Dependencies installed with `poetry install`
- Database migrated with `poetry run flask --app scaffold:create_app db upgrade`
- Threat, risk, and BIA modules enabled in the local or test environment
- At least one authenticated user with permission to edit threat models

## Manual validation flow

1. Create or open a PASTA threat model and confirm the existing seven-stage workflow remains intact.
2. Complete enough upstream analysis to reach stage seven and add at least one `risk_conclusion` finding.
3. Enter likelihood and impact scores for the conclusion and confirm the UI shows the derived overall score or priority using the same scoring language as the current threat and risk experience.
4. Confirm the conclusion remains non-publishable if likelihood, impact, or the risk outcome narrative is missing.
5. Publish the eligible conclusion to the risk workspace and confirm a linked risk record appears there with traceability back to the PASTA model.
6. Change upstream PASTA content so the conclusion becomes stale and confirm the conclusion is flagged for revalidation and blocked from republish until it is current again.
7. Revalidate the conclusion, republish it, and confirm the existing linked risk is refreshed rather than duplicated.
8. Review the PASTA model in the interactive UI and export it as HTML, PDF, and CSV to confirm stage-seven scores, publish state, and linked risk references render in the application's established style.
9. Open the linked risk in the risk workspace and confirm the source PASTA linkage is visible without letting the risk workspace become the new source of truth.

## Automated validation targets

Run the narrowest relevant slices first while implementing:

```powershell
poetry run pytest tests/test_threat_pasta_routes.py tests/test_threat_pasta_exports.py -k "pasta"
```

Expected follow-up slices after the new tests are added:

```powershell
poetry run pytest tests/test_threat_pasta_routes.py tests/test_threat_pasta_exports.py tests/test_threat_pasta_workflow.py -k "risk or publish or export"
```

If publication behavior is split into a dedicated module, run that targeted slice as well.

## Migration validation

1. Generate the Alembic migration for the new structured PASTA risk-conclusion persistence.
2. Apply the migration to a database that already contains PASTA stage and finding data.
3. Verify existing PASTA models remain readable and editable after the migration.
4. Verify current STRIDE scenario-to-risk sync still works.
5. Verify newly published PASTA conclusions create or refresh linked risk records without duplicate rows.

## Audit and localization checks

- Confirm score edits, publish actions, republish actions, and blocked publication attempts emit attributable audit events.
- Confirm new stage-seven labels, publish-state badges, and export terminology resolve through translation keys in English and Dutch.

## Completion criteria

- Guided PASTA stage seven captures structured likelihood and impact scoring.
- Publication is explicit, gated, and idempotent.
- PASTA remains the source of truth after publication.
- Risk workspace entries are traceable projections, not duplicate authoritative records.
- Interactive UI, HTML, PDF, and CSV reporting all reflect the new stage-seven scoring and publish state.