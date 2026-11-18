---
type: decision
id: 20261118-1530-ssp-usability-checklist-gap-resolutions
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/ssp/models.py
  - scaffold/apps/ssp/forms.py
  - scaffold/apps/ssp/routes.py
  - scaffold/apps/ssp/services.py
  - scaffold/apps/ssp/templates/ssp/*
  - scaffold/apps/admin/routes.py
  - docker/nginx/nginx.conf
  - docker/nginx/nginx.conf.example.*.md
  - docs/deployment.md
  - migrations/versions/*
tags: [ssp, checklist, gap-resolution, security, nginx]
participants: [Ferry Stelte, Claude]
---

# SSP usability pass: checklist gap resolutions

Resolves the items in
`specs/20261118-144354-ssp-metadata-interconnections-adr/checklists/general.md`.
It amends decisions 20261118-1455, -1500, -1505, -1510 and -1515 where noted.
The user made the calls marked **(user)**. The others follow the codebase's
defaults and conventions.

## Context

The general requirements checklist found 25 gaps. These cover ADR
supersession, reconcile edge cases, upload limits, PDF serving, roles,
wording and testability. While checking CHK008 we also found that the
bundled `docker/nginx/nginx.conf` sets no `client_max_body_size`. nginx
therefore applies its 1 MB default and answers larger uploads with a raw 413
before the app sees them. This is the most likely root cause of "the
architecture overview does not always upload".

## Resolutions

### ADR supersession and delete
- **CHK001 (user): store and restore the prior status.** A new column
  `adr_records.status_before_supersede` (non-native enum like `status`,
  nullable) is set when `add_adr` supersedes an ADR. Deleting the superseding
  ADR restores exactly that status and clears the column. The fallback for
  legacy rows where it is NULL is `accepted`. (Amends 20261118-1515.)
- **CHK017:** the either/or rule (external link, or context + decision) lives
  in one shared form-level validator that `ADRCreateForm` and `ADRUpdateForm`
  both use. Removing the link from a link-only ADR during edit then requires
  context and decision.

### Interconnection reconcile
- **CHK002 (user): adopt.** When a BIA name matches an existing `manual` row
  (normalised), that row is converted to `source='bia'` and keeps its details.
  No duplicate row is added.
- **CHK003 (user): block deleting live BIA rows.** A `bia` row whose name is
  still in the BIA cannot be deleted. The button is disabled with the hint
  "Remove it from the BIA interfaces first", and the server returns a flash
  error with a redirect. Stale `bia` rows and `manual` rows can be deleted.
  (Amends 20261118-1455.)
- **CHK004: normalisation.** Strip, collapse internal whitespace to a single
  space, then `casefold()`. Duplicate names in the BIA text are de-duplicated,
  and the first occurrence decides the stored spelling.
- **CHK009: audit.** A reconcile that adds or adopts rows writes one
  `ssp_interconnections_reconciled` event with `added` and `adopted` name
  lists. The `ssp_updated` details now include `law_option_ids` and
  `monitoring_frequency_id`.
- **CHK025: concurrency.** Before it adds rows, reconcile locks the SSP row
  with `SELECT … FOR UPDATE` (`with_for_update()`, which is a no-op on
  SQLite where writes are serialised) and computes the missing names again
  under the lock. Two simultaneous first views therefore cannot create
  duplicates. No unique constraint is needed.

### Admin option lists
- **CHK005: ordering.** Options are listed alphabetically by name.
  `sort_order` is **dropped** from `SSPOption` because nothing needs a manual
  order. (Amends 20261118-1500.)
- **CHK006: uniqueness.** Name uniqueness is case-insensitive per kind and is
  checked in the route with `func.lower`, like authentication-method slugs. A
  duplicate gives a flash and a field error, "An option with this name
  already exists". The DB unique constraint stays on (`kind`, `name`).
- **CHK007: frequency seeding.** Existing values are grouped by their
  normalised form (CHK004 rule). Each group becomes one option, with the
  first-seen trimmed spelling as its name.
- **CHK014: inactive options.** In the edit form an inactive option that the
  SSP already uses is shown as "Name (inactive)". The view and print show the
  name only.

### Architecture overview
- **CHK008: request-size limits.** Add `client_max_body_size 12m;` (10 MB
  file plus multipart overhead) to the `server` block in
  `docker/nginx/nginx.conf` and to both example configs. Also document it in
  `docs/deployment.md`, together with a note that an upstream load balancer
  needs at least the same limit. Do **not** set Flask's `MAX_CONTENT_LENGTH`
  globally, because it would also cap the admin backup-restore upload. The
  10 MB check stays in `FileSize`.
- **CHK010: version numbers.** The rule is: the next version is the highest
  *remaining* `version_number` + 1, so a deleted top number may be reused.
  The text "never reused" is removed from 20261118-1505.
- **CHK020 (user): PDFs are downloaded, not shown inline.** The stream route
  serves `application/pdf` with `Content-Disposition: attachment;
  filename="<original_filename>"` and `nosniff`. The card button reads
  "Download PDF". Images stay `inline`. (Amends 20261118-1505.)
- **CHK013: error keys.** The new or changed translation keys under
  `ssp.architecture_overview.upload.errors.` are:
  - `invalid_type` (not PNG, JPEG or PDF)
  - `invalid_image` (corrupt image)
  - `invalid_pdf` (missing `%PDF-` header)
  - `too_large` (over 10 MB)
  - `dimensions_too_large` (image over 8000 px)
  - `required`

  The help text key is `ssp.architecture_overview.upload.help`.

### Roles and security
- **CHK019 (user): any logged-in user may delete** architecture-overview
  versions and ADRs. This is the same as every other SSP mutation today (POA&M
  items, interconnections, the SSP itself). Mitigations are a confirm prompt,
  CSRF and an audit event. The residual risk is a mistaken or malicious
  delete by an authenticated user, and the audit trail records the actor.
  This goes in the release notes. The admin options page stays admin-only
  with a fresh login.
- **CHK021: the Jira link may point to any http(s) host.** No Jira base URL
  setting, because that would add configuration for little value. The
  validation is the shared absolute-http(s) check.
- **CHK016: one shared validator.** `validate_external_url` in
  `ssp/forms.py` (absolute `http`/`https`, max 500 characters) is used for
  `adr_register_url`, `ADRRecord.external_url` and `POAMItem.jira_url`. Every
  external link renders with `target="_blank" rel="noopener noreferrer"`. The
  print export shows the URL as text.
- **CHK022:** every new destructive POST uses a `FlaskForm` / `csrf_token()`
  and the existing confirm-prompt pattern on the templates. This covers delete
  version, delete ADR, and admin option toggle and delete.

### Wording, consistency, coverage
- **CHK011:** milestones count as a value, so the POA&M "Details (optional)"
  block opens when any detail field is set or when milestones exist.
  (Amends 20261118-1510.)
- **CHK012:** the EN wording is fixed in the design (§7). The NL translation
  is written in the same task, and Ferry reviews it.
- **CHK015:** "Security ADRs" is used on the SSP view nav button, the view
  section header, the ADR list title, add/edit page titles, the print/PDF
  section header and the docs.
- **CHK018:** the print/PDF export shows option names, the ADR register URL,
  Jira URLs, link-only ADRs ("Described externally: <url>") and stale
  interconnections with the suffix "(no longer in BIA)".
- **CHK023:** a US7 acceptance scenario is added to the design.
- **CHK024:** partial restore orders tables from the live schema's FK graph
  (`get_sorted_table_and_fkc_names` in `admin/backup_utils.py`), so the new
  tables are picked up automatically. Task 2 adds a test for backup and
  partial restore with `ssp_options` and `ssp_plan_laws` rows as evidence.

## Consequences

### Positive
- ✅ Fixes the probable real upload failure (nginx 1 MB)
- ✅ No ADR status is lost on delete; supersession stays consistent
- ✅ Reconcile is free of duplicates, even with concurrent views

### Negative
- ❌ One more column (`status_before_supersede`) in the migration
- ❌ PDFs have to be downloaded to view them
- ❌ The nginx change requires redeploying the gateway container
