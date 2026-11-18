---
feature: 20261118-144354-ssp-metadata-interconnections-adr
branch: 20261118-074624-risk-workspace-sync-bia-filter
status: planned
created: 2026-11-18
chunk_size: adaptive
total_tasks: 12
estimated_lines: 1295
---

# SSP Usability Pass Tasks

## Overview

Implements [design.md](design.md):
- Fixes the SSP metadata save.
- Interconnections are reconciled from the BIA's `interfaces`.
- Laws/regulations/policies and monitoring frequency come from admin-managed
  lists.
- The architecture overview accepts PDFs and allows deletion, with upload
  guidance.
- POA&M is Jira-first.
- ADRs are security-only, can link externally and can be deleted.
- The monitoring and POA&M purpose wording is clarified.

Tests go in each task. New EN/NL strings are added in the task that introduces
them (`scaffold/translations/en.json`, `nl.json`). Task 11 only checks
completeness.

## Task List

### Foundation

#### Task 1: Fix SSP metadata save [P]
- **Estimate:** ~40 lines
- **Parallel:** Can run with Task 6
- **Files:** `scaffold/apps/ssp/forms.py`, `scaffold/apps/ssp/routes.py` (`edit`), `tests/test_ssp_routes.py`
- **Description:** Remove `fips_confidentiality/integrity/availability` from `SSPEditForm`, along with the assignments and GET prefill in `routes.edit`. The DB columns stay. (Decision `20261118-1450`.)
- **Depends on:** None
- **Acceptance:** A POST to `ssp.edit` with laws and monitoring fields (and no FIPS fields) redirects to the view and persists the values.
- **Evidence:** A new regression test fails on the current code and passes after the fix. `pytest tests/test_ssp_routes.py` is green.

#### Task 2: Models and single migration
- **Estimate:** ~175 lines
- **Files:** `scaffold/apps/ssp/models.py`, `scaffold/apps/ssp/forms.py` (frequency field removal, `validate_external_url`), `scaffold/apps/ssp/routes.py` (`edit`: frequency assignment), `scaffold/apps/ssp/templates/ssp/view.html`, `print.html` (frequency rendering), `migrations/versions/20261118_0003_ssp_usability_pass.py` (new; `revision = "20261118_0003"`, `down_revision = "20261118_0002"`), `tests/test_ssp_routes.py` or the migration test location used by earlier features, `tests/test_admin_partial_restore.py`
- **Description:** Add the following:
  - `SSPOptionKind` enum and `SSPOption` model (unique `kind`+`name`, `is_active`, `description`, timestamps; no `sort_order`, options are listed alphabetically)
  - `ADRRecord.status_before_supersede` (nullable, ADR status values)
  - `ssp_plan_laws` M2M and `SSPlan.laws_regulations_options`
  - `SSPlan.monitoring_frequency_id`, an FK with SET NULL, plus the relationship
  - `SSPlan.adr_register_url`
  - `SSPInterconnection.source` (non-native enum `bia`/`manual`, server default `manual`)
  - `POAMItem.jira_url`
  - `ADRRecord.external_url`
  - `ADRRecord.context`/`decision` made nullable

  Migration data steps:
  - group the non-empty `monitoring_frequency` values by normalised form (strip, collapse whitespace, casefold), seed one option per group using the first-seen trimmed spelling, link each SSP, then drop `monitoring_frequency`;
  - backfill `source='bia'` where the normalised name matches the scope's parsed `interfaces`.

  Put the normalise/parse helper in `ssp/services.py` so that Task 3 reuses it; the migration keeps its own inline copy, because migrations must not import app code.

  `laws_regulations` stays as a dormant column (resolved open question).

  Keep the app working after the column drop (analyze C1). Remove `monitoring_frequency` from `SSPEditForm`, remove its assignment in `routes.edit`, and have `view.html`/`print.html` render `ssp.monitoring_frequency_option.name` (or "—"). Task 5 adds the select.

  Add the shared `validate_external_url` WTForms validator to `ssp/forms.py` (absolute `http`/`https`, max 500 characters), with unit tests. Tasks 5, 8 and 9 reuse it (analyze W1).
- **Depends on:** Task 1 (same form and route lines)
- **Acceptance:** Upgrade and downgrade run on SQLite and PostgreSQL. "Monthly" and "monthly " become one linked option. Seeded interconnections are marked `bia`. Partial restore of a backup with `ssp_options` and `ssp_plan_laws` rows succeeds.
- **Evidence:** `flask db upgrade` / `downgrade -1` / `upgrade` succeed on both engines. The migration data test, the partial-restore test (new case in `tests/test_admin_partial_restore.py`) and the validator tests pass. The full `pytest` suite is green.

### Core Implementation

#### Task 3: Interconnection reconcile from BIA [P]
- **Estimate:** ~150 lines
- **Parallel:** Can run with Tasks 4, 5, 8
- **Files:** `scaffold/apps/ssp/services.py`, `scaffold/apps/ssp/routes.py` (`create`, `view`, `edit`, `interconnections`, `edit_interconnection`, `delete_interconnection`, `export_pdf`), `scaffold/apps/ssp/templates/ssp/interconnections.html`, `edit_interconnection.html`, `view.html`, `print.html`, `tests/test_ssp_routes.py`
- **Description:** `reconcile_interconnections(ssp)` replaces `seed_interconnections`. It is idempotent and works as follows:
  - normalise names (strip, collapse whitespace, casefold); duplicates in the BIA text are dropped and the first spelling wins;
  - lock the SSP row (`with_for_update()`), then compute the missing names again under the lock;
  - add missing `bia` rows and adopt matching `manual` rows as `bia`;
  - never delete;
  - commit only when something changed, and then write the audit event `ssp_interconnections_reconciled` (`added`, `adopted`).

  Call it from the listed routes.

  UI and route rules:
  - stale `bia` rows show a "No longer in BIA" badge; print shows the suffix "(no longer in BIA)";
  - on `bia` rows, `system_name` is read-only and ignored on POST;
  - deleting a live `bia` row is disabled in the UI with a hint, and the route refuses it with a flash and redirect.

  Rewrite the existing `tests/test_ssp_routes.py::test_seed_interconnections_from_interfaces` against `reconcile_interconnections`, and remove the `seed_interconnections` import from `routes.py` (analyze W3).

  (Decisions `20261118-1455`, `20261118-1530`.)
- **Depends on:** Task 2
- **Acceptance:** Tests cover add-on-view, no duplicates on a second view, the stale flag, untouched manual rows, a manual row being adopted, normalisation (`" a  b "` matches `"A B"`), a rename attempt being ignored, live-BIA delete refused while stale delete works, and the audit event being written. Concurrency is covered by design (the row lock); there is no automated race test.
- **Evidence:** New tests pass. `pytest tests/test_ssp_routes.py` is green.

#### Task 4: Admin SSP option lists page [P]
- **Estimate:** ~170 lines
- **Parallel:** Can run with Tasks 3, 5, 8
- **Files:** `scaffold/apps/admin/routes.py`, `scaffold/apps/admin/forms.py`, `scaffold/apps/admin/templates/admin/ssp_options.html` (new), `scaffold/apps/admin/templates/admin/users.html` (hub link), `tests/test_admin_ssp_options.py` (new)
- **Description:** `/admin/ssp-options` has two sections (laws/regulations/policies, monitoring frequencies), listed alphabetically, with create, edit, toggle active and delete. Names are unique per kind, case-insensitively (`func.lower`, like authentication-method slugs); a duplicate gives a flash and a field error. An option that is in use is deactivated instead of deleted. Every POST form uses CSRF, and delete/toggle use a confirm prompt. Requires admin and fresh login, following `list_authentication_methods`. Audit events: `ssp_option_created/updated/toggled/deleted`. (Decision `20261118-1500`.)
- **Depends on:** Task 2
- **Acceptance:** A non-admin gets 403. Create, edit and toggle work. Creating "nis2" when "NIS2" exists is rejected. Deleting an unused option removes it; deleting an in-use option deactivates it. The hub link is present.
- **Evidence:** `pytest tests/test_admin_ssp_options.py` is green.

#### Task 5: SSP edit/view/print, list selection, ADR register URL, monitoring wording [P]
- **Estimate:** ~110 lines
- **Parallel:** Can run with Tasks 3, 4, 8
- **Files:** `scaffold/apps/ssp/forms.py`, `scaffold/apps/ssp/routes.py` (`edit`), `scaffold/apps/ssp/templates/ssp/edit.html`, `view.html`, `print.html`, `tests/test_ssp_routes.py`
- **Description:** Make these changes:
  - Replace the laws textarea with a `SelectMultipleField` and the frequency text with a `SelectField` that has an empty choice. Choices are alphabetical: active options, plus inactive ones already linked to this SSP labelled "Name (inactive)". The view and print show the name only.
  - Add `adr_register_url`, validated with `validate_external_url` (from Task 2).
  - View and print render option names and the register link (`target="_blank" rel="noopener noreferrer"`; URL text in print).
  - Add `law_option_ids` and `monitoring_frequency_id` to the `ssp_updated` audit details.
  - Add the continuous-monitoring intro (EN text in design §7, NL translation for Ferry to review) on edit, view and print.
- **Depends on:** Task 1 (same form, route and template; analyze W5), Task 2 (tests seed options directly; Task 4 not required)
- **Acceptance:** Selected laws and frequency persist and render. An inactive linked option survives a save and shows the "(inactive)" suffix in the form only. A `javascript:` register URL is rejected. The audit details contain the selection. The intro text renders in EN and NL (US7).
- **Evidence:** New tests pass. `pytest tests/test_ssp_routes.py` is green.

#### Task 6: Architecture overview, PDF support, upload guidance and gateway limit [P]
- **Estimate:** ~130 lines
- **Parallel:** Can run with Task 1 (no schema dependency)
- **Files:** `scaffold/apps/ssp/forms.py`, `scaffold/apps/ssp/routes.py` (`upload_architecture_overview`, `architecture_overview_image`), `scaffold/apps/ssp/templates/ssp/view.html`, `docker/nginx/nginx.conf`, `docker/nginx/nginx.conf.example.behind-proxy.md`, `docker/nginx/nginx.conf.example.public.md`, `docs/deployment.md`, `tests/test_ssp_architecture_overview.py`
- **Description:** Make these changes:
  - Accept `.pdf` and validate it by its `%PDF-` magic bytes.
  - Raise the limit to 10 MB; the 8000 px check applies to images only.
  - Take `mime_type` from the detected content.
  - Add `accept=".png,.jpg,.jpeg,.pdf"` and the help text `ssp.architecture_overview.upload.help`.
  - Use distinct error keys: `invalid_type`, `invalid_image`, `invalid_pdf`, `too_large`, `dimensions_too_large`, `required`.
  - Show a PDF as a file card with "Download PDF". The stream route serves PDFs as `attachment; filename="<original_filename>"` with `nosniff`; images stay `inline`.
  - **Gateway:** add `client_max_body_size 12m;` to the `server` block of `nginx.conf` and to both example configs, because the 1 MB nginx default was the likely real upload failure. Document it in `docs/deployment.md`, including a note that an upstream load balancer needs at least the same limit. Leave Flask's `MAX_CONTENT_LENGTH` unset.

  CSP is not changed. (Decisions `20261118-1505`, `20261118-1530`.)
- **Depends on:** None
- **Acceptance:** A PDF upload is stored as `application/pdf`, rendered as a card and served with `Content-Disposition: attachment`. A renamed non-PDF gives `invalid_pdf`, an SVG gives `invalid_type`, and a file over 10 MB gives `too_large`. An image sent as `octet-stream` is stored with its real MIME type. `nginx -t` accepts the config.
- **Evidence:** `pytest tests/test_ssp_architecture_overview.py` is green. `docker run --rm -v $PWD/docker/nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro nginx nginx -t` succeeds (or the equivalent for the gateway image). A manual 5 MB upload through the gateway in a dev stack succeeds.

#### Task 7: Architecture overview, delete per version
- **Estimate:** ~60 lines
- **Files:** `scaffold/apps/ssp/routes.py` (new `delete_architecture_overview`), `scaffold/apps/ssp/templates/ssp/view.html`, `tests/test_ssp_architecture_overview.py`
- **Description:** `POST /ssp/<id>/architecture-overview/<version_id>/delete` deletes the version, after a confirm prompt in the UI (CSRF form), and writes the audit event `ssp_architecture_overview_deleted`. Any logged-in user may delete (decision `20261118-1530`, CHK019). Delete buttons appear on the current version and on each history entry. The next upload uses max(remaining) + 1.
- **Depends on:** Task 6 (same files)
- **Acceptance:** Deleting the current version makes the previous one current. Deleting the only version shows "None uploaded". A version of another SSP gives 404. The audit entry is written.
- **Evidence:** New tests pass.

#### Task 8: POA&M Jira-first [P]
- **Estimate:** ~110 lines
- **Parallel:** Can run with Tasks 3, 4, 5
- **Files:** `scaffold/apps/ssp/forms.py`, `scaffold/apps/ssp/routes.py` (`add_poam_item`, `edit_poam_item`), `scaffold/apps/ssp/templates/ssp/poam_item_form.html`, `poam.html`, `view.html`, `print.html`, `tests/test_ssp_routes.py`
- **Description:** Add `jira_url` (optional, `validate_external_url` from Task 2, any host). The primary block holds weakness, status and Jira link. A collapsed "Details (optional)" block holds contact, date, resources, cost and milestones, and opens when any detail field has a value or milestones exist. The Jira link is shown on the list, the view (external, `noopener`) and print (URL text). The purpose intro on list, view and form reads "steering and monitoring improvements to the system in this plan". (Decision `20261118-1510`.)
- **Depends on:** Task 2
- **Acceptance:** An item with only weakness, status and Jira link saves. A `ftp:`/`javascript:` link is rejected. The link renders in all three places. An item with only milestones opens the details block.
- **Evidence:** New tests pass.

#### Task 9: ADR external link, either/or rule, "Security ADRs" wording
- **Estimate:** ~120 lines
- **Files:** `scaffold/apps/ssp/forms.py` (`ADRCreateForm`, `ADRUpdateForm`), `scaffold/apps/ssp/routes.py` (`add_adr`, `edit_adr`, `adrs`), `scaffold/apps/ssp/templates/ssp/add_adr.html`, `edit_adr.html`, `adr_detail.html`, `adrs.html`, `view.html`, `print.html`, `tests/test_ssp_adr.py`
- **Description:** Make these changes:
  - Add an optional `external_url` (`validate_external_url`). Context and decision are required unless a link is set; one shared form-level validator is used by both `ADRCreateForm` and `ADRUpdateForm`. Store empty values as NULL.
  - When `add_adr` supersedes an ADR, store its current status in `status_before_supersede` before setting it to `superseded`.
  - The detail page shows "Described externally → link" and hides empty context/decision blocks. Print shows "Described externally: <url>".
  - The ADR list and the view section show `ssp.adr_register_url` at the top.
  - Use "Security ADRs" on the view nav button, the view section header, the list title, the add/edit page titles and the print header. Add the intro from design §7 and form help text.

  (Decision `20261118-1515`.)
- **Depends on:** Task 2, Task 5 (register URL field)
- **Acceptance:** An ADR with only a link saves. Without a link, missing context or decision gives a form error, on create and on edit (including removing the link from a link-only ADR). Superseding a `proposed` ADR stores `proposed` in `status_before_supersede`. The register link is shown when set.
- **Evidence:** `pytest tests/test_ssp_adr.py` is green.

#### Task 10: ADR delete with unlink and restore
- **Estimate:** ~70 lines
- **Files:** `scaffold/apps/ssp/routes.py` (new `delete_adr`), `scaffold/apps/ssp/templates/ssp/adr_detail.html`, `adrs.html`, `tests/test_ssp_adr.py`
- **Description:** `POST /ssp/<id>/adrs/<adr_id>/delete` runs in one transaction:
  - the predecessor goes back to its `status_before_supersede` (fallback `accepted` when NULL), the column is cleared, and the audit event `adr_unsuperseded` is written;
  - the successor's `supersedes_id` is cleared;
  - the audit event `adr_deleted` is written;
  - secondary principles are removed through the M2M cascade.

  The UI asks for confirmation first.
- **Depends on:** Task 9 (same files)
- **Acceptance:** Deleting a standalone ADR works. Deleting a successor restores the predecessor to its earlier status (for example `proposed`), or to `accepted` for a legacy row where the column is NULL. Deleting a predecessor clears the successor's link without an FK error. An ADR of another SSP gives 404.
- **Evidence:** New tests pass on SQLite. The FK behaviour is checked on PostgreSQL if available.

#### Task 12: Risk owner from threat owner [P]
- **Estimate:** ~80 lines
- **Parallel:** Can run with any task (separate module, no schema change)
- **Files:** `scaffold/apps/threat/services.py` (`sync_scenario_to_risk`, `publish_pasta_conclusion_to_risk`, `_risk_sync_snapshot`), `scaffold/apps/risk/templates/risk/form.html`, the admin risk edit owner field (check which template renders it: `admin/risk_edit.html` includes `admin/_risk_form.html`, which refers to `form.owner_id`), `scaffold/translations/en.json`, `nl.json`, `tests/test_threat_risk_sync.py`
- **Description:** Make these changes:
  - On create and every re-sync, set `risk.treatment_owner_id = scenario.owner_id or scenario.threat_model.owner_id`, and `None` when neither is set.
  - PASTA publish uses the threat model owner of the conclusion (through finding → stage record → threat model).
  - Add `treatment_owner_id` to `_risk_sync_snapshot` so the sync audit shows owner changes.
  - For risks linked to a scenario or a PASTA conclusion, show the hint "Set from the threat owner; the next threat sync overwrites this" under the owner select on the risk edit page and the admin risk edit page. The field stays editable.

  The approval reset needs no new code; the existing listener handles it. (Decision `20261118-1545`.)
- **Depends on:** None
- **Acceptance:** Tests cover:
  - the scenario owner being used;
  - the model owner when the scenario has none;
  - the owner being cleared when neither is set;
  - a manual change being overwritten at the next sync;
  - an approved risk being reset when sync changes the owner;
  - a PASTA-published risk getting the model owner;
  - `risk_synced_from_threat` details including the owner change;
  - the hint appearing only for threat-linked risks.
- **Note:** adding `treatment_owner_id` to `_risk_sync_snapshot` changes the audit `changes` diff. Update any existing assertions in `tests/test_threat_risk_sync.py` that compare the snapshot exactly.
- **Evidence:** `pytest tests/test_threat_risk_sync.py tests/test_risk_approval.py` is green.
- **Implementation note:** the hint is on `risk/form.html` only. `GET /admin/risks/<id>` already returns 500 before this work: `admin/_risk_form.html` renders `form.category`, `form.owner_id`, `form.probability` and `form.status`, none of which exist on `RiskForm`. Repairing that page is out of scope here and is reported as a follow-up.

### Integration & Polish

#### Task 11: Translations, docs, release notes, graph update
- **Estimate:** ~80 lines
- **Files:** `scaffold/translations/en.json`, `nl.json`, `docs/ssp.md` (new; the user-facing guide for these behaviours), `specs/20261118-144354-ssp-metadata-interconnections-adr/release-notes.md` (new), `graphify-out/`
- **Description:** Make these changes:
  - Check that every new key exists in EN and NL and that no hard-coded strings were added.
  - Document: BIA-driven interconnections, the admin lists, upload rules (PNG/JPEG/PDF, 10 MB), Jira-first POA&M, security-only ADRs with external links and delete.
  - Write the release notes, including the migration and the removed free-text fields.
  - Run `graphify update .`.
- **Depends on:** Tasks 1–10, 12
- **Acceptance:** No missing translation keys. The docs describe every user-visible change.
- **Evidence:** The translation key diff between `en.json` and `nl.json` is empty for the new keys. The full `pytest` suite is green. `graphify update .` succeeds.

## Notes
- Work stays on branch `20261118-074624-risk-workspace-sync-bia-filter` (user request).
- `laws_regulations` and the `fips_*` columns stay dormant. Drop them in a later cleanup.
- Reconcile writes during GET; this is accepted and idempotent (decision `20261118-1455`).
- External links are always validated as absolute http(s) and rendered with `rel="noopener noreferrer"`.
- Partial restore orders tables from the live FK graph, so the new tables need no code change. Task 2 adds the test.
- Checklist gaps are resolved in decision `20261118-1530`. The Task 6 nginx change requires redeploying the gateway container; say so in the release notes, together with the "any logged-in user may delete" risk (CHK019).- Out of scope: Jira API integration, inline PDF preview, per-locale option labels, link checking, writing back to the BIA.

## Progress
- [x] Task 1: Fix SSP metadata save
- [x] Task 2: Models and single migration
- [x] Task 3: Interconnection reconcile from BIA
- [x] Task 4: Admin SSP option lists page
- [x] Task 5: SSP edit/view/print, list selection, ADR register URL, monitoring wording
- [x] Task 6: Architecture overview, PDF support, upload guidance and gateway limit
- [x] Task 7: Architecture overview, delete per version
- [ ] Task 8: POA&M Jira-first
- [ ] Task 9: ADR external link, either/or rule, "Security ADRs" wording
- [ ] Task 10: ADR delete with unlink and restore
- [x] Task 12: Risk owner from threat owner
- [ ] Task 11: Translations, docs, release notes, graph update
