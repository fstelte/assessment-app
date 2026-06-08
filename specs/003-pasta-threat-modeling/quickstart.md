# Quickstart: PASTA Threat Modeling

## Goal

Validate the planned PASTA workflow end to end in the existing threat module before implementation is considered complete.

## Prerequisites

- Dependencies installed with `poetry install`
- Database migrated with `poetry run flask --app scaffold:create_app db upgrade`
- Threat module available in a local dev environment or test environment
- At least one user with admin or assessment-manager role

## Manual validation flow

1. Create a new threat model with `methodology=PASTA`.
2. Confirm the model initializes seven canonical stages and only stage 1 is initially available.
3. Complete the minimum content for stage 1 and confirm stage 2 unlocks while stage 1 remains editable.
4. Add findings in stages 2 through 6 and verify that STRIDE-LM mappings are optional per finding.
5. Edit an earlier completed stage and confirm affected later stages are marked for revalidation rather than silently remaining current.
6. Generate or link a standard threat scenario from a selected PASTA finding and confirm the relationship is visible in the PASTA review surface.
7. Bootstrap a new PASTA model from an existing STRIDE-LM model and confirm the source model remains reviewable and unchanged in place.
8. Export the PASTA model as HTML, PDF, and CSV and confirm methodology-aware output and traceability to any linked/generated scenarios.

## Automated validation targets

Run the most targeted test slice first while implementing:

```powershell
poetry run pytest tests/test_threat_routes.py -k "pasta or threat"
```

If export behavior is split into a separate test module during implementation, run that targeted slice as well.

## Migration validation

1. Generate the migration for any new PASTA tables or `threat_models` columns.
2. Apply the migration on a database containing existing STRIDE-LM models.
3. Verify those existing models remain viewable and editable without forced conversion.
4. Verify a bootstrap-created PASTA model records the source-model traceability.

## Audit and localization checks

- Confirm create, bootstrap, stage update, finding update, scenario-link, and export actions emit audit events.
- Confirm all new workflow labels and export terminology resolve through translation keys in English and Dutch.

## Completion criteria

- PASTA workflow is model-level and stage-aware.
- Ordered progression, light gating, and revalidation are visible to the user.
- STRIDE-LM reuse is optional and finding-specific.
- Downstream standard threat-scenario linkage is traceable.
- Existing STRIDE-LM models and exports remain functional.
