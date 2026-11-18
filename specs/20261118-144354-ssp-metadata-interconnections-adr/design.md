---
feature: ssp-metadata-interconnections-adr
branch: 20261118-074624-risk-workspace-sync-bia-filter
status: implemented
created: 2026-11-18
decisions:
  - 20261118-1450-ssp-edit-drop-fips-overrides
  - 20261118-1455-ssp-interconnections-reconciled-from-bia
  - 20261118-1500-ssp-admin-option-lists
  - 20261118-1505-architecture-overview-pdf-and-delete
  - 20261118-1510-poam-jira-first-minimal-item
  - 20261118-1515-adr-external-links-and-delete
  - 20261118-1530-ssp-usability-checklist-gap-resolutions
  - 20261118-1545-risk-owner-from-threat-owner
---

# SSP Usability Pass: Metadata Fix, BIA Interconnections, Admin Lists, Architecture Uploads, POA&M Jira, Security ADRs

## Overview

This is a set of fixes and refinements to the System Security Plan module
(`scaffold/apps/ssp/`). It fixes the SSP metadata edit, which never saves. It
makes the BIA's interfaces the source of SSP interconnections. Laws/regulations/
policies and monitoring frequency become admin-managed lists. The architecture
overview accepts PDFs and allows deleting uploads, with clear upload guidance.
POA&M becomes Jira-first. ADRs are explicitly security-only, can be deleted and
can point to external documentation. The copy now explains what continuous
monitoring and POA&M are for. This work is developed on the existing branch
`20261118-074624-risk-workspace-sync-bia-filter` at the user's request.

## User Stories

- **US1 (P1, bug)**: As an SSP editor, I want my metadata edits to save, so that
  the plan reflects reality.
- **US2 (P1)**: As an SSP editor, I want interconnections to come from the BIA's
  interfaces automatically, so that the two never drift. I still record
  agreement type, direction and contact in the SSP.
- **US3 (P2)**: As an admin, I want to maintain the list of laws, regulations
  and policies, and the list of monitoring frequencies, from the admin hub
  (`/admin/users`). As an SSP editor, I want to pick from those lists: laws as
  multi-select, frequency as single-select.
- **US4 (P2)**: As an SSP editor, I want to know exactly what I can upload as
  the architecture overview (PNG, JPEG or PDF, size limits). I also want to
  remove an upload that was wrong.
- **US5 (P2)**: As a system owner, I want the POA&M to be a steering view of the
  improvements on this system, with each item linking to its Jira issue, so I
  don't author tasks twice.
- **US6 (P3)**: As an architect, I want to record only security-related ADRs. I
  want to delete an ADR, and to link to our ADR page (for the whole SSP, or per
  ADR) instead of re-typing it.
- **US7 (P3)**: As a reader, I want "Continuous monitoring" to say that it is
  about monitoring progress on this SSP.
- **US8 (P2)**: As a risk manager, I want the owner defined on a threat to be
  the owner of the risk it syncs to, so that threat-derived risks have an owner
  (and can go through owner approval) without manual work.

### Acceptance scenarios

1. **US1**: Given an SSP, when I change any metadata field and save, then the
   value is persisted and shown on the SSP view. A regression test covers a
   POST without FIPS fields.
2. **US2**: Given a BIA with interfaces `A; B`, when I open the SSP, then rows A
   and B exist with source `bia`. After `C` is added in the BIA, opening the
   SSP adds C. After `A` is removed from the BIA, row A shows the badge "No
   longer in BIA" and is not deleted. A manual row is never flagged. The system
   name of a `bia` row cannot be changed through the edit form. A manual row
   named ` a ` becomes the `bia` row for interface `A` (no duplicate). A live
   `bia` row cannot be deleted; a stale one can. Two concurrent first views
   create no duplicates.
3. **US3**: Given active law options, when I edit an SSP, then I can select
   several, and the view and print show their names. Given an option that is in
   use, when an admin deletes it, then it is deactivated instead. It stays on
   SSPs that already use it and is no longer offered for new selections.
4. **US4**: Given a valid PDF of 10 MB or less, when I upload it, then it becomes
   the current version and shows as a file card with "Download PDF". The file
   is served as an attachment. Given an SVG or an 11 MB file, then the error
   names the exact reason. A 5 MB upload through the bundled nginx gateway
   reaches the app (no 413). When I delete the
   current version, then the previous one becomes current. When I delete the
   only version, then "None uploaded" is shown.
5. **US5**: When I create a POA&M item with only weakness, status and an https
   Jira link, then it saves, and the link appears on the POA&M list and the SSP
   view. A non-http(s) link is rejected.
6. **US6**: When I create an ADR with title, principle, status and an external
   link but no context/decision, then it saves. Without a link, context and
   decision are required. When I delete an ADR that superseded another, then
   the other goes back to the status it had before it was superseded (for
   example `proposed`), or to `accepted` for legacy rows. When I delete an ADR
   that a successor superseded, then the successor's `supersedes` link is
   cleared.
7. **US7**: Given the SSP edit page, view or print, then the continuous-
   monitoring section starts with the intro text from §7, in EN and NL.
8. **US8**: Given a scenario owned by Alice in a model owned by Bob, when it
   syncs, then the risk owner is Alice. Given a scenario without an owner, the
   risk owner is Bob. If neither is set, the risk owner is cleared. If a user
   changes the owner on a linked risk, the next sync overwrites it back, and
   the owner select shows a hint saying so. A sync that changes the owner of
   an approved risk resets the approval. A PASTA-published risk gets the
   threat model's owner. The sync audit records the owner change.

## Components

### 1. Metadata edit fix (`forms.py`, `routes.edit`)
Remove `fips_confidentiality/integrity/availability` from `SSPEditForm`, along
with their assignments and GET prefill in `routes.edit`. The columns stay. Add a
regression test. → decision `20261118-1450`.

### 2. Interconnection reconcile (`services.reconcile_interconnections`)
This replaces `seed_interconnections`. It parses `ContextScope.interfaces`
(newline / `;`). Names are normalised by stripping, collapsing whitespace and
`casefold()`; duplicates in the BIA text are dropped (first spelling wins).
Under a `with_for_update()` lock on the SSP row it adds missing `bia` rows,
adopts a matching `manual` row as `bia`, never deletes, and commits (with audit
`ssp_interconnections_reconciled`) only when something changed. It is called
from `create`, `view`, `interconnections`, `edit` and `print`/PDF. Templates
show a "No longer in BIA" badge for stale `bia` rows ("(no longer in BIA)" in
print). On `bia` rows, `system_name` is read-only in the edit form and ignored
on POST. Live `bia` rows cannot be deleted: the button is disabled with a hint
and the server refuses. → decisions `20261118-1455`, `20261118-1530`.

### 3. SSP option lists (`SSPOption` model + admin page)
A generic catalogue with a `kind` field (`law_regulation`,
`monitoring_frequency`). Laws link to the SSP through the M2M `ssp_plan_laws`;
frequency is a FK `SSPlan.monitoring_frequency_id`. The admin page
`/admin/ssp-options` (admin role and fresh login required, audit events) is
linked from the `/admin/users` hub. Edit form: `SelectMultipleField` for laws,
`SelectField` for frequency with an empty choice. Options are listed
alphabetically; in-use inactive options appear as "Name (inactive)" in the
edit form only. Names are unique per kind, case-insensitively. The free-text
laws field is removed from the UI. → decisions `20261118-1500`, `20261118-1530`.

### 4. Architecture overview uploads
Accepts PNG/JPEG/PDF up to 10 MB; images are limited to 8000 px. PDFs are
validated by their `%PDF-` magic bytes. The MIME type comes from the detected
content. The input gets an `accept` attribute and the help text
`ssp.architecture_overview.upload.help`. Errors have distinct keys
(`invalid_type`, `invalid_image`, `invalid_pdf`, `too_large`,
`dimensions_too_large`, `required`). A PDF is shown as a file card with
"Download PDF" and is served as `attachment`; images stay inline. CSP is
unchanged. Delete is available per version
(`POST …/architecture-overview/<version_id>/delete`) with a confirm prompt and
an audit event. The next version is max(remaining) + 1.

**Gateway:** the bundled nginx had no `client_max_body_size`, so the 1 MB
default rejected larger uploads with a raw 413. This was the likely real cause
of "does not always upload". Set `client_max_body_size 12m;` in
`docker/nginx/nginx.conf` and in both example configs, and document it in
`docs/deployment.md`, including the upstream load-balancer note. Flask's
`MAX_CONTENT_LENGTH` stays unset, so the backup-restore upload is not capped.
→ decisions `20261118-1505`, `20261118-1530` (partially supersedes `20260829-1230`).

### 5. POA&M Jira-first
New field `POAMItem.jira_url` (optional, http(s)). The primary form block holds
weakness, status and Jira link. Contact, date, resources, cost and milestones
sit in a collapsed "Details (optional)" block, which opens when any of them has
a value or milestones exist. The Jira link may point to any http(s) host. Jira links are shown on the list, the view and print. An intro text
states the purpose (steering and monitoring improvements to the system in this
plan). → decision `20261118-1510`.

### 6. Security ADRs
New fields: `SSPlan.adr_register_url` (edited in the metadata form) and
`ADRRecord.external_url`. `context`/`decision` become nullable. One shared
form-level validator, used on both create and edit, requires either a link or
both context and decision. When `add_adr` supersedes an ADR, it stores
`status_before_supersede`. Delete (`POST /ssp/<id>/adrs/<adr_id>/delete`)
restores the predecessor to that status (fallback `accepted`), clears a
successor's link and writes audit events. "Security ADRs" is used on the nav
button, the view section, the list, the add/edit titles, print and docs.
→ decisions `20261118-1515`, `20261118-1530`.

All three URL fields use one validator, `validate_external_url` in
`ssp/forms.py` (absolute http/https, max 500 characters). They render with
`target="_blank" rel="noopener noreferrer"`, and as text in print.

### 8. Risk owner from threat owner (risk/threat modules)
This is outside the SSP module and was added to this workstream at the
user's request. `sync_scenario_to_risk` sets `risk.treatment_owner_id =
scenario.owner_id or scenario.threat_model.owner_id` on create and on every
re-sync, clearing it when neither is set. `publish_pasta_conclusion_to_risk`
uses the conclusion's threat model owner. The field stays editable on the risk
edit pages; for threat-linked risks it gets the hint "Set from the threat
owner; the next threat sync overwrites this". `_risk_sync_snapshot` gains
`treatment_owner_id`, so the change is audited. Approval resets go through the
existing listener. There is no migration or backfill: existing risks update
at their next sync. → decision `20261118-1545`.

### 7. Copy-only clarifications
EN wording is fixed here. The implementing task writes the NL translation and
Ferry reviews it.
- **Continuous monitoring** (edit, view `CM`, print): "Continuous monitoring
  describes how progress on this System Security Plan is tracked: which KPIs
  and KRIs are measured, what is monitored, who does it, with which tools and
  how often."
- **POA&M** (list, view section, item form): "The POA&M is used to steer and
  monitor improvements to the system described in this plan. Record each
  weakness here and track the detailed work in Jira."
- **Security ADRs** (list, view section, add/edit): "Record only
  security-relevant architecture decisions for this system, for example
  authentication, encryption, network segmentation or logging. Link to your
  ADR page instead of copying it when the decision is documented elsewhere."
- All new strings go through `_()` / `_l()` with EN and NL translations
  (Constitution IV).

## Data Model

One Alembic migration:

| Change | Detail |
|---|---|
| `ssp_options` (new) | `id`, `kind` (non-native enum), `name` String(255), `description` Text NULL, `is_active` bool default true, `created_at`, `updated_at`; unique (`kind`, `name`) |
| `ssp_plan_laws` (new) | `ssp_id` FK → `ssp_plans.id` CASCADE, `option_id` FK → `ssp_options.id` CASCADE, composite PK |
| `ssp_plans.monitoring_frequency_id` | FK → `ssp_options.id`, `ondelete=SET NULL`. The data step groups existing `monitoring_frequency` values by normalised form, seeds one option per group (first-seen trimmed spelling), links each SSP, then drops `monitoring_frequency` |
| `ssp_plans.adr_register_url` | String(500) NULL |
| `ssp_interconnections.source` | non-native enum `bia`/`manual`, NOT NULL, server default `manual`; the data step backfills `bia` on a normalised name match with the scope's interfaces |
| `ssp_poam_items.jira_url` | String(500) NULL |
| `adr_records.external_url` | String(500) NULL |
| `adr_records.context`, `.decision` | change to NULL-able |
| `adr_records.status_before_supersede` | non-native enum (ADR status values), NULL |

Backup and partial restore: partial restore orders tables from the live
schema's FK graph (`get_sorted_table_and_fkc_names` in
`admin/backup_utils.py`), so the new tables are picked up automatically. Task 2
adds a test with `ssp_options` and `ssp_plan_laws` rows.

## API / Interface

| Route | Method | Change |
|---|---|---|
| `ssp.edit` | GET/POST | no FIPS fields; laws multi-select; frequency select; `adr_register_url` |
| `ssp.view`, `ssp.interconnections`, `ssp.create`, print/PDF | GET/POST | call `reconcile_interconnections` |
| `ssp.edit_interconnection` | POST | ignores `system_name` for `bia` rows |
| `ssp.delete_interconnection` | POST | refuses live `bia` rows (flash + redirect) |
| `ssp.architecture_overview_image` | GET | PDFs served as `attachment` |
| `ssp.upload_architecture_overview` | POST | PNG/JPEG/PDF, 10 MB, detected MIME |
| `ssp.delete_architecture_overview` (new) | POST | `/ssp/<id>/architecture-overview/<version_id>/delete` |
| `ssp.add_poam_item`, `ssp.edit_poam_item` | GET/POST | `jira_url`; collapsed details |
| `ssp.add_adr`, `ssp.edit_adr` | GET/POST | `external_url`; either/or validation |
| `ssp.delete_adr` (new) | POST | `/ssp/<id>/adrs/<adr_id>/delete` |
| `admin.ssp_options` (new) | GET/POST | `/admin/ssp-options`: list and create; edit, toggle and delete as POST sub-routes like authentication methods |

**Security and audit (Constitution II):**
- **Roles:** SSP routes stay `@login_required`, so any logged-in user may
  delete architecture-overview versions and ADRs, as with every other SSP
  mutation today. Mitigations are CSRF, a confirm prompt and an audit event
  that records the actor. The residual risk is a mistaken or malicious delete
  by an authenticated user; this is stated in the release notes. The admin
  page requires an admin and a fresh login.
- **New audit events:** `ssp_architecture_overview_deleted`, `adr_deleted`,
  `adr_unsuperseded`, `ssp_interconnections_reconciled`,
  `ssp_option_created/updated/toggled/deleted`. The `ssp_updated` details gain
  `law_option_ids` and `monitoring_frequency_id`.
- **Links and files:** external links are validated as absolute http(s), which
  blocks `javascript:` URLs. User PDFs are never rendered from the app origin.
  Every new destructive POST uses CSRF tokens.

## Testing (Constitution III)

Extend `tests/test_ssp_routes.py`, `tests/test_ssp_architecture_overview.py` and
`tests/test_ssp_adr.py`, plus admin option tests:
- edit POST persists fields (regression)
- reconcile: add, stale flag, no duplicate, manual untouched, manual adopted,
  read-only name, live-BIA delete refused, normalisation, audit event
- options: multi/single save, deactivate-in-use, admin-only, case-insensitive
  duplicate, inactive suffix
- uploads: PDF ok and served as attachment, bad magic rejected, >10 MB
  rejected, MIME detected, delete current/only
- POA&M: Jira-only item saves, bad scheme rejected, details open with
  milestones
- ADR: link-only ADR saves, either/or rule on create and edit, delete with both
  chain directions, prior status restored
- threat→risk owner (`tests/test_threat_risk_sync.py`): scenario owner, model
  fallback, cleared, overwrite of a manual change, approval reset, PASTA, audit
  snapshot
- migration upgrade/downgrade on SQLite and PostgreSQL; frequency
  de-duplication; partial restore including the new tables

## Constitution Check

| Area | Confirmation |
|---|---|
| **Module ownership (I)** | SSP models, forms, routes, services and templates stay in `scaffold/apps/ssp/`. The `SSPOption` admin page lives in `scaffold/apps/admin/` with the model in `ssp`, the same pattern as `ArchitecturePrinciple`. Task 12 changes `scaffold/apps/threat/services.py`, which already projects scenarios onto `Risk`; no new cross-domain path. Shared code stays in the owning module, and nothing moves to `scaffold/core/`. |
| **Security and audit (II)** | Roles: SSP mutations, including the new deletes, are open to any logged-in user (unchanged policy, risk recorded in decision `20261118-1530`, CHK019). The admin options page requires admin and fresh login. New audit events are listed under API/Interface. External links are restricted to http(s). User PDFs are served as attachments. CSP is unchanged. |
| **Tests and migrations (III)** | One Alembic migration (`20261118_0003`) with upgrade, downgrade and data steps, tested on SQLite and PostgreSQL. Each task bundles pytest coverage; the regression test for the save bug is in Task 1. |
| **UI and localization (IV)** | Tailwind and the existing macros (`render_field_with_help`). All strings go through `_()`/`_l()` with EN and NL. Exports (print/PDF) carry the same terms as the UI ("Security ADRs", "(no longer in BIA)", option names). |
| **Operations (V)** | Gateway: `client_max_body_size 12m` in `docker/nginx/nginx.conf` and the examples, documented in `docs/deployment.md`. The release needs a gateway container redeploy and `flask db upgrade`. No new environment variables. `MAX_CONTENT_LENGTH` stays unset, so backup restore is unaffected. |
| **Docs** | `docs/ssp.md` (new) and release notes in Task 11; `docs/deployment.md` in Task 6. |

## Out of Scope

- Jira API integration (status sync, issue creation); links only
- Inline PDF preview (PDFs are downloaded by design)
- Restricting the Jira link to a configured host
- Per-locale labels for option lists
- Checking that external links still resolve
- Two-way sync to the BIA (the SSP never writes back to `interfaces`)
- Removing the dormant `fips_*` columns

## Open Questions

- ~~**`laws_regulations` column**: drop or keep?~~ Resolved in `/minispec.tasks`:
  **leave dormant** (non-destructive, same as the FIPS columns).
- Should the print/PDF export include the architecture overview? It does not
  today, and this design does not change that.
