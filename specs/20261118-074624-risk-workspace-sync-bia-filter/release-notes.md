# Release notes: risk workspace targeted sync, BIA filter and actual risk score

## What's new

- **Synced risks link only the affected components.** A risk created from a
  threat scenario now links just the BIA components that the scenario lists as
  threatened assets. The match is by name, ignoring case and surrounding
  spaces. Before, a scenario with no match linked every component in the BIA.
- **Filter the risk workspace by BIA.** You can select one or more BIAs. The
  risk cards, the summary figures and the matrix then only show risks with a
  component in those BIAs. The filter is part of the URL
  (`/risk/?bia=3&bia=7`), so you can bookmark or share it.
- **The actual risk is shown.** Every risk can now record a residual impact,
  a residual chance and a "Mitigated" marker. When a risk is mitigated and has
  both residual values, the residual score is used everywhere. Otherwise the
  initial score is used. This applies to:
  - the risk cards (with an "Initial: X → Residual: Y" hint);
  - the risk matrix;
  - the "High & critical" count;
  - the risk edit page;
  - the admin risk register;
  - the SSP risk summary (on screen and in the PDF export).
- **Threat-linked risks follow their scenario.**
  - A scenario with status **Mitigated** now keeps its risk open, with the
    residual score. Before, it closed the risk.
  - **Accepted** and **Closed** still close the risk. So does a scenario
    whose treatment isn't Mitigate.
  - On the risk form, the fields the scenario controls are read-only and link
    to the scenario: title, description, impact, chance, treatment, residual
    values, Mitigated, components and controls.
- **Audit trail.** Changes made by the sync are logged as
  `risk_synced_from_threat`, listing only the fields that changed, and new
  risks as `risk_created_from_threat`. Manual create and update events now
  include the mitigated marker and the residual values.
- **API.** `GET /api/risks` adds `mitigated_at`, `residual_impact`,
  `residual_chance`, `residual_score`, `actual_score` and `actual_severity`.
  `score` and `severity` still mean the initial score. `POST` and `PUT` accept
  `residual_impact`, `residual_chance` and `mitigated`. A field you leave out
  stays unchanged, and `null` clears it.

## Behaviour changes to be aware of

1. **Synced risks lose components on their next sync.** Risks that got every
   component in the BIA through the old fallback keep only the components that
   match the scenario's threatened assets. If nothing matches, they keep none.
   The change is visible in the audit log.
2. **Archived risks of mitigated scenarios reopen.** Before, mitigated
   scenarios archived their risk. On the next sync (saving the scenario,
   "Sync from threats", or opening the risk) such risks reopen as mitigated.
3. **Opening a threat-linked risk syncs it.** The edit page refreshes the risk
   from its scenario. If the scenario is Accepted or Closed, that closes the
   risk.
4. **The "Mitigation tracks" figure is now called "Treatment: mitigate".** It
   still counts risks whose treatment is mitigate.

## Fixes

- An API `PUT` that kept one of the risk's existing impact areas failed with
  a 500 error (unique constraint `uq_risk_impact_area`).

## Upgrade

- Migration `20261118_0001` adds three nullable columns to `risk_items`:
  `mitigated_at`, `residual_impact` and `residual_chance`. Existing rows need
  no backfill. Their actual score equals their initial score until they are
  synced or edited. It runs with the usual `flask db upgrade` during
  deployment.
- **Downgrade** drops the three columns, and the mitigated and residual data
  is lost.
- Tested: upgrade, then downgrade, then upgrade again, on PostgreSQL 16.

## Known limitations and follow-ups

- The API can still change fields of a threat-linked risk that the scenario
  owns. The next sync overwrites them.
- The SSP risk summary counts a risk once for each component it has in that
  BIA, so one risk can be counted twice. This was already the case.
- PASTA-published risks have no residual values from PASTA. You can set them
  by hand on the risk form.
