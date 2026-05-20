# Quickstart: Threat Model and Risk Updates

## 1. Apply schema changes

```powershell
poetry run flask --app scaffold:create_app db upgrade
```

## 2. Verify threat scenario multi-select behavior

1. Sign in as an admin or assessment manager.
2. Open an existing threat model with at least two assets.
3. Create or edit a scenario using methodology `STRIDE`.
4. Select multiple assets and multiple STRIDE-LM categories.
5. Save the scenario and reopen it.
6. Confirm all selected assets and categories persist on the form, detail page, model detail view, and exports.

## 3. Verify risk multi-ticket-link behavior

1. Open an existing risk or create a new one.
2. Add two ticket links, each with a label and URL.
3. Save and reopen the risk.
4. Confirm the ticket links display in the edit form, dashboard/detail surfaces, and API payload.

## 4. Run focused automated validation

```powershell
poetry run pytest tests/test_threat_routes.py tests/test_risk_routes.py tests/test_risk_api.py
```

## 5. Spot-check compatibility contracts

1. Download threat CSV export and confirm both compatibility columns (`asset`, `stride_category`) and plural columns (`assets`, `stride_categories`) are populated as designed.
2. Call `GET /api/risks` and confirm the response includes `ticket_links` plus the deprecated compatibility alias `ticket_url`.

## 6. Review localization and audit behavior

1. Confirm new form labels, validation messages, and summary text resolve through translation keys.
2. Confirm audit entries are produced for multi-assignment scenario updates and risk ticket-link changes.