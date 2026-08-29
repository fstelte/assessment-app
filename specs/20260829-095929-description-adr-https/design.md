# Feature Specification: Architecture Decision Records (ADR) on the System Security Plan

**Feature Branch**: `20260829-095929-description-adr-https`
**Created**: 2026-08-29
**Status**: Complete
**Input**: User description: "add ADR (https://adr.github.io/) to the System Security Plan, where the record starts with selecting one of the architecture principles which an admin can create in the same manner as the control catalogue administration, also make it so that the principles can be bulk imported, give an example of a file that can be used to import."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin manages the Architecture Principle catalogue (Priority: P1)

An admin needs a governed list of architecture principles (e.g. "Prefer managed services", "Least privilege by default") that authors can select from when writing an ADR, so that decisions are traceable back to agreed principles instead of free text.

**Why this priority**: Nothing else in this feature works without the catalogue existing first — an ADR cannot be created until at least one principle exists.

**Independent Test**: Log in as an admin, go to `/admin/principles`, create a principle, edit it, delete it. Fully testable without any ADR or SSP involved.

**Acceptance Scenarios**:

1. **Given** an admin is on the Architecture Principles admin page, **When** they submit a new principle with a unique name and description, **Then** it appears in the catalogue and becomes selectable on new ADRs.
2. **Given** a principle is already referenced by at least one ADR, **When** an admin attempts to delete it, **Then** the system blocks the delete and explains which ADRs reference it (mirrors the existing control-in-use guard).
3. **Given** a non-admin user, **When** they navigate to `/admin/principles`, **Then** they receive the same "insufficient role" response as `/admin/controls`.

---

### User Story 2 - Admin bulk-imports architecture principles (Priority: P1)

An admin who already maintains a corporate list of architecture principles (e.g. in a wiki or another GRC tool) wants to upload them in one action instead of creating each one by hand.

**Why this priority**: Directly requested; without it, seeding a realistic catalogue for a new tenant/organization is impractical.

**Independent Test**: Upload a JSON file with several principles on `/admin/principles`, confirm created/updated/skipped counts, confirm the principles now exist in the catalogue.

**Acceptance Scenarios**:

1. **Given** a valid `principles.json` file (see example below), **When** an admin uploads it, **Then** each principle is created if new, or updated in place if a principle with the same `name` already exists (upsert), and an import summary (created/updated/errors) is shown — matching the existing control import summary UX.
2. **Given** a file that is not valid JSON, or valid JSON not matching the expected shape, **When** an admin uploads it, **Then** the system rejects the import with a clear per-row or file-level error and imports nothing partially.
3. **Given** a file containing a mix of valid and invalid principle entries, **When** an admin uploads it, **Then** valid entries import and invalid entries are reported by row/name in the error list, without aborting the whole batch.

---

### User Story 3 - Author creates an ADR on a System Security Plan (Priority: P1)

A user documenting an SSP wants to record an architecture decision in the standard ADR format (adr.github.io: Title, Status, Context, Decision, Consequences), anchored to one of the org's approved architecture principles.

**Why this priority**: This is the core feature being requested — everything else exists to support it.

**Independent Test**: From an SSP's ADR tab, start "New ADR", pick a principle first, fill in the remaining fields, save, and see it listed on the SSP.

**Acceptance Scenarios**:

1. **Given** an SSP with at least one architecture principle in the catalogue, **When** a user starts a new ADR, **Then** they must select exactly one primary architecture principle before the rest of the form is enabled/saved (principle selection gates the record, per adr.github.io's decision-driven framing).
2. **Given** an ADR being created, **When** the user optionally selects one or more secondary principles, **Then** those are stored as additional (non-primary) links to the same ADR.
3. **Given** an SSP with no architecture principles defined yet, **When** a user tries to start a new ADR, **Then** they see a message directing them to ask an admin to add principles (or a link to the admin page, if they hold that role), instead of a broken/empty picker.
4. **Given** an existing Accepted ADR, **When** a user creates a new ADR and marks it as superseding the old one, **Then** the old ADR's status automatically becomes "Superseded" and displays a link to the new ADR (and vice versa).

---

### User Story 4 - Reviewer reads ADRs in context of the SSP (Priority: P2)

A reviewer/auditor opens an SSP and wants to see the architecture decisions behind it, filterable by principle and status, without leaving the SSP. "Reviewer" here is not a distinct role: it means any authenticated user who already has view access to the SSP — reading ADRs requires no additional permission beyond what's already needed to view the SSP itself. Only *administering the Architecture Principle catalogue* (User Stories 1–2) requires the elevated `admin`/`ROLE_CONTROL_OWNER` role (FR-011).

**Why this priority**: Read/review value; can ship after creation works, but is needed for the feature to be useful to anyone but the author.

**Independent Test**: Open an SSP with several ADRs in different statuses, filter by principle and by status, open one to view full detail including its supersession chain.

**Acceptance Scenarios**:

1. **Given** an SSP with multiple ADRs, **When** a reviewer opens the SSP's ADR tab, **Then** ADRs are listed with Title, Status, primary Principle, and date, ordered newest first.
2. **Given** an ADR that supersedes or was superseded by another, **When** a reviewer opens it, **Then** both directions of the link are visible and clickable.

---

### Edge Cases

- What happens when the selected primary principle is later deleted? — Prevented: deletion of a principle referenced by any ADR is blocked (User Story 1, Scenario 2), so this cannot occur.
- What happens if an ADR is marked as superseding an ADR that already has a `superseded_by` link? — Rejected with a validation error ("this ADR is already superseded by X"); an ADR can be superseded at most once.
- What happens on a bulk import where the same `name` appears twice in the same file? — Last occurrence wins for the upsert, and the earlier occurrence is reported as a "duplicate in file, overwritten" note in the import summary (mirrors how repeated rows are handled in `import_controls_from_mapping`).
- What happens if a principle name in the import file matches an existing principle only by case (`"Least Privilege"` vs `"least privilege"`)? — Match is case-insensitive on `name` for upsert, to avoid accidental duplicates.
- What happens when an ADR references a principle from a different SSP's context? — Not applicable: the Architecture Principle catalogue is global (like the Control catalogue), not scoped per SSP, so any principle is valid for any SSP's ADRs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an admin-only catalogue of Architecture Principles (`name`, `description`), manageable via create/edit/delete/bulk-delete, following the same route, form, and permission pattern as the existing Control catalogue admin (`scaffold/apps/admin/routes.py` `controls()` view).
- **FR-002**: System MUST support bulk import of Architecture Principles from an uploaded JSON file, upserting by `name` (matched case-insensitively, after trimming leading/trailing whitespace and Unicode casefolding). On a match, the stored `description` MUST be overwritten with the imported value (last-write-wins; no merge). MUST return a created/updated/errors summary, following the same pattern as `import_controls_from_mapping()` in `scaffold/apps/csa/services/control_importer.py`. If the same `name` (after normalization) appears more than once within one import file, the last occurrence in file order wins and earlier occurrences MUST be reported in the summary as superseded-within-file.
- **FR-003**: System MUST prevent deleting an Architecture Principle that is referenced (as primary or secondary) by any existing ADR at the time of the delete request, and MUST report the blocking ADRs. This check is evaluated dynamically against current references, so a principle that becomes unreferenced (e.g. after its only referencing ADR is removed via SSP cascade delete, FR-009) becomes deletable immediately afterward — there is no stale-guard window. Bulk-import upserts (FR-002) are exempt from this guard (updates, not deletes).

  *Note: this deliberately diverges from `Control`, which has no delete-time use-guard — `delete_control()` (`scaffold/apps/admin/routes.py:425-455`) deletes unconditionally and cascades to its `AssessmentTemplate` children. That's acceptable for `AssessmentTemplate` (regenerable working data); it is not acceptable for an ADR's principle reference (a compliance/audit record whose "why" would silently go dangling), so Architecture Principle intentionally adds the guard Control lacks.*
- **FR-004**: System MUST allow creating an ADR on a System Security Plan only after a primary Architecture Principle has been selected; the primary principle is required (`NOT NULL` at the database level) and immutable after creation. Enforcement: the ADR edit form MUST NOT expose a field for changing `primary_principle_id`, and the update route MUST reject any request payload that attempts to change it, independent of the form (defense in depth, consistent with Principle II of the constitution). Changing the core decision driver requires creating a new ADR, optionally marked as superseding this one (FR-008).
- **FR-005**: System MUST allow optionally attaching zero or more secondary Architecture Principles to an ADR, distinct from the primary one.
- **FR-006**: System MUST capture the adr.github.io fields on each ADR: Title, Status, Context, Decision, Consequences, plus authorship (`author_id`) and timestamps.
- **FR-007**: System MUST support the following status lifecycle, and MUST reject any transition not listed:
  - `Proposed → Accepted`
  - `Proposed → Rejected`
  - `Accepted → Deprecated` (manual retirement, no replacement ADR)
  - `Accepted → Superseded` (only via FR-008's supersede action, never a direct manual status edit)
  - No transition is defined out of `Rejected`, `Deprecated`, or `Superseded` — those are terminal; correcting course means authoring a new ADR.
- **FR-008**: System MUST allow an ADR to declare it supersedes exactly one prior ADR, and the picker for that prior ADR MUST be scoped to ADRs within the same SSP only (a cross-SSP selection MUST be rejected as a validation error, not merely prevented by UI). On save, the prior ADR's status MUST become "Superseded" immediately and unconditionally — regardless of the new (superseding) ADR's own status — and both records MUST expose the link (`supersedes` / `superseded_by`) in the UI. An ADR that is already `superseded_by` another MUST NOT be selectable as a supersede target again (at most one supersession per ADR). Because "Superseded" is only reachable via this action (FR-007), an ADR can never be simultaneously manually-`Deprecated` and superseded — the two terminal states are mutually exclusive by construction.
- **FR-009**: System MUST scope ADRs to a single SSP via `ssp_id`, cascading delete when the parent SSP is deleted (matching `SSPControlEntry`/`SSPInterconnection` behavior).
- **FR-010**: System MUST list an SSP's ADRs with filters for status and principle, ordered by most recent first, using the same paginated-query pattern as the control catalogue list (`query.paginate(page=..., per_page=50, error_out=False)`, `scaffold/apps/admin/routes.py:198`) rather than loading the full set unpaginated. The Architecture Principle admin list MUST use the same pagination pattern.
- **FR-011**: System MUST enforce the same role checks for principle administration as control administration: a user MUST hold role `admin` or `ROLE_CONTROL_OWNER` (`scaffold/apps/identity/models.py`, reused via `_require_control_admin()`'s pattern) — no new role is introduced for this feature.
- **FR-012**: System MUST record an audit-log entry (via the existing `log_event()` helper, `entity_type="architecture_principle"` / `"adr_record"`) for: principle create, update, delete, and bulk import (create/update counts); and for ADR create and every status change (including supersession). This follows Constitution Principle II (Security, Auditability, and Least Surprise), which mandates audit visibility for admin-controlled data.
- **FR-013**: All user-facing strings for the Architecture Principle admin UI and the ADR UI (labels, flash messages, validation errors, import-summary text) MUST be routed through the project's localization helpers (`lazy_gettext`/`gettext`, matching the `admin.controls.*` translation-key convention), per Constitution Principle IV.
- **FR-014**: When a user without the `admin`/`ROLE_CONTROL_OWNER` role opens "New ADR" on an SSP with zero Architecture Principles defined, the system MUST display a message stating that no principles exist yet and that an admin must add them, with no further action available. When a user *with* that role opens the same empty state, the message MUST additionally include a direct link to `/admin/principles`.

### Key Entities

- **Architecture Principle**: A reusable, admin-governed catalogue entry (`name`, `description`) that ADRs are anchored to. Global, not scoped to a single SSP — analogous to `Control`.
- **ADR (Architecture Decision Record)**: Belongs to exactly one SSP. Has a required primary Architecture Principle, optional secondary Architecture Principles, adr.github.io fields (title, status, context, decision, consequences), authorship/timestamps, and an optional self-referential supersession link to another ADR in the same SSP.
- **ADR–Secondary Principle link**: Association between an ADR and zero-or-more non-primary Architecture Principles.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In the app's standard admin environment, uploading the 4-entry example file in this document (or an equivalent up to 50 entries) completes and shows an import summary in under a minute — verified by the pytest import task, not just observed manually.
- **SC-002**: A user cannot save a new ADR without first choosing a primary architecture principle (0% of saved ADRs have a null primary principle) — enforced at two layers: `primary_principle_id` is `NOT NULL` at the database schema level (belt), and the ADR creation form rejects submission without it (suspenders, FR-004).
- **SC-003**: 100% of ADRs marked "Superseded" have a resolvable link to the ADR that superseded them, and vice versa — verified automatically by the supersession pytest task (see tasks.md), which asserts both directions of the relationship after a supersede action, not by manual inspection.
- **SC-004**: Reviewers can locate all ADRs tied to a given principle across an SSP in a single filtered view, with no manual cross-referencing.

## Design Notes (implementation grounding)

This section records where the implementation should sit, based on the existing codebase (see decision records for the full rationale):

- **Models** (`scaffold/apps/ssp/models.py`, alongside `SSPlan`, `SSPControlEntry`):
  - `ArchitecturePrinciple` — `id`, `name` (unique, case-insensitive), `description`, `created_at`, `updated_at`.
  - `ADRRecord` — `id`, `ssp_id` (FK → `ssp_plans.id`, cascade delete), `title`, `status` (enum: proposed/accepted/deprecated/rejected/superseded), `context`, `decision`, `consequences`, `primary_principle_id` (FK → principle, required), `supersedes_id` (nullable self-FK), `author_id` (FK → users), `decided_on` (nullable date), `created_at`, `updated_at`.
  - `ADRSecondaryPrinciple` — association table: `adr_id`, `principle_id`.
- **Admin CRUD** (`scaffold/apps/admin/routes.py`, `scaffold/apps/admin/forms.py`): new `principles()` view at `/admin/principles` plus `/create`, `/<id>/edit`, `/<id>/update`, `/<id>/delete`, `/delete-bulk` sub-routes, reusing `_require_control_admin()`-style permission check and `@login_required` / `@require_fresh_login()`. Forms: `PrincipleCreateForm`, `PrincipleUpdateForm(PrincipleCreateForm)`, `PrincipleDeleteForm`, `PrincipleImportForm` (JSON `FileField`), mirroring `ControlCreateForm`/`ControlImportForm`.
- **Import service** (`scaffold/apps/ssp/principle_importer.py`): `import_principles_from_mapping(payload)` mirroring `import_controls_from_mapping()`; payload shape `{"principles": [{"name": ..., "description": ...}]}`; upsert by case-insensitive `name`; returns `ImportStats(created, updated, errors)`.
- **SSP integration** (`scaffold/apps/ssp/routes.py`, `scaffold/apps/ssp/templates/ssp/`): new "ADRs" tab on the SSP detail view; "New ADR" form gated on principle selection as step 1.
- **Migrations**: new Alembic revision(s) under `migrations/versions/` for `architecture_principles`, `adr_records`, `adr_secondary_principles` tables, following the naming convention of the existing `..._ssp*.py` migrations.

### Example bulk-import file (`principles.json`)

```json
{
  "principles": [
    {
      "name": "Least Privilege by Default",
      "description": "Grant the minimum access required for a role or service to perform its function; expand access only with documented justification."
    },
    {
      "name": "Prefer Managed Services",
      "description": "Use cloud-managed services over self-hosted equivalents unless a documented constraint (cost, compliance, latency) requires otherwise."
    },
    {
      "name": "Encrypt Data In Transit and At Rest",
      "description": "All data, internal or external, must be encrypted using approved algorithms both while stored and while moving between systems."
    },
    {
      "name": "Single Source of Truth per Domain",
      "description": "Each data domain has exactly one authoritative system of record; other systems consume copies, never compete as the source."
    }
  ]
}
```

## Open Questions

- **Resolved**: does declaring `supersedes` require the superseding ADR to be "Accepted" first? No — per FR-008, the old ADR's status flips to "Superseded" immediately on save, regardless of the new ADR's own status, matching adr.github.io's simple model. Revisit only if a formal review/approval workflow is added later.
- Should Architecture Principles support soft-delete/archive instead of hard delete-when-unused? Out of scope for this feature. Hard delete is used, but — unlike `Control`, which has no use-guard at all (see FR-003's note) — Architecture Principle adds a use-guard because an unreferenced deletion is safe while a referenced one would orphan a compliance record.
- **Out of scope**: exporting or printing ADRs as part of an SSP export. The rest of the SSP already supports export elsewhere in the app; extending that to ADRs is a natural follow-up but is not required for this feature to deliver value, and is deferred rather than assumed.
- **Out of scope / accepted assumption**: concurrent bulk-imports of the Architecture Principle catalogue by two admins at once are not specially handled — last commit wins, same as any other admin catalogue edit in this app today. This is a reasonable assumption for a small internal admin tool with infrequent catalogue edits; revisit only if concurrent-admin usage becomes common.

---

# Feature Specification: Architecture Overview Image on the System Security Plan

**Feature Branch**: `20260829-095929-description-adr-https` (same branch as the ADR feature above)
**Created**: 2026-08-29
**Status**: Planned
**Input**: User description: "a way to create or upload an architecture overview to the SSP, make it visible in the SSP /ssp/."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Author uploads an architecture overview image (Priority: P1)

Any authenticated user working on an SSP wants to upload a PNG or JPEG diagram (e.g. exported from a drawing tool) showing the system's architecture, so reviewers can see the system's shape at a glance without leaving the SSP.

**Why this priority**: This is the entire feature — nothing else has value without it.

**Independent Test**: Open an SSP's overview page, upload a PNG, see it displayed on the page immediately after.

**Acceptance Scenarios**:

1. **Given** an SSP with no architecture overview yet, **When** a logged-in user uploads a valid PNG or JPEG, **Then** it becomes the current architecture overview and is displayed on the SSP overview page.
2. **Given** an SSP that already has an architecture overview, **When** a user uploads a new PNG/JPEG, **Then** the new image becomes current and the previous one is kept in history (not deleted).
3. **Given** a non-image file (e.g. `.pdf`, `.exe`) or an oversized file, **When** a user attempts to upload it, **Then** the upload is rejected with a clear validation error and nothing is stored.

---

### User Story 2 - Reviewer views architecture overview history and restores an older version (Priority: P2)

A user reviewing the SSP wants to see previously uploaded architecture overview images (e.g. to compare how the diagram evolved) and, if the current one was uploaded by mistake, bring an older one back as current.

**Why this priority**: Builds on Story 1; the app is fully usable (single current image) without it, but was explicitly requested as versioned history with restore.

**Independent Test**: Upload two different images to the same SSP, open the history list, restore the first one, confirm it is now shown as current and a third history entry now exists recording the restore.

**Acceptance Scenarios**:

1. **Given** an SSP with multiple architecture overview versions, **When** a user opens the overview page, **Then** they see the current image plus a list of prior versions with uploader and timestamp, newest first.
2. **Given** a past (non-current) version, **When** a user clicks "restore" on it, **Then** a **new** version is created with the same image bytes, becomes current, and is audit-logged as a restore (no existing row is edited or deleted — history stays append-only).

---

### Edge Cases

- What happens when the uploaded file's extension says `.png` but the content isn't actually a valid image? — Rejected: the file is decoded/verified as an image server-side (not just checked by extension/MIME header) before it is stored.
- What happens when the SSP is deleted? — All architecture overview versions for that SSP are cascade-deleted, matching `SSPInterconnection`/`SSPControlEntry`/`ADRRecord` behavior (FR-009 in the ADR spec above).
- What happens on restoring the version that is already current? — No-op from the user's perspective is avoided by not offering a "restore" action on the current version in the UI; if it were ever requested (e.g. race), the system MAY still create a new identical version rather than erroring, since that's harmless and simpler than special-casing it.
- What happens with a very large image? — Rejected above a fixed size cap (5 MB) with a clear error, to keep the database blob small and predictable (Constitution Principle V).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow any authenticated user with access to an SSP (i.e. anyone who can reach `ssp.view`/`ssp.edit` today — no new role) to upload a PNG or JPEG image as that SSP's architecture overview, matching the permission model of the existing `ssp.edit` route (`@login_required` only, no role check). This same permission model (authenticated, no new role) MUST also gate the restore action and the image-serving route — all three architecture-overview routes require `@login_required` and nothing more, identical to `ssp.edit`.
- **FR-002**: System MUST verify the upload is a decodable PNG or JPEG image (not just trust the filename/MIME header) and MUST reject anything else, and MUST reject files larger than 5 MB, with a clear validation error in both cases.
- **FR-003**: System MUST store the image bytes in the database (not on the container filesystem), since no user-upload volume is mounted in the deployment today (Constitution Principle V — no hidden local-disk production dependency).
- **FR-004**: System MUST keep every uploaded architecture overview as an immutable, append-only version (never edited or deleted individually), ordered by an incrementing version number per SSP. The current version is the one with the highest version number for that SSP — no separate "is current" flag is needed.
- **FR-005**: System MUST display the current architecture overview image directly on the SSP overview page (`ssp/view.html`), near the other overview fields (authorization boundary, FIPS ratings).
- **FR-006**: System MUST let a user view the version history (uploader, timestamp) for an SSP's architecture overview and restore any past version; restoring MUST create a new version with the same image bytes (copy-forward) rather than mutating or reordering existing rows.
- **FR-007**: System MUST record an audit-log entry (via the existing `log_event()` helper, `entity_type="ssp_architecture_overview"`) for every upload and every restore, including which version number was restored from for restores, per Constitution Principle II.
- **FR-008**: System MUST cascade-delete all architecture overview versions when their parent SSP is deleted, matching existing SSP child-entity behavior.
- **FR-009**: All user-facing strings (upload form, validation errors, history labels, restore confirmation) MUST be routed through the project's localization helpers, per Constitution Principle IV.

### Key Entities

- **SSP Architecture Overview Version**: Belongs to exactly one SSP. Holds the raw image bytes, MIME type (`image/png` or `image/jpeg`), original filename, file size, uploader, and upload timestamp, plus an SSP-scoped incrementing version number. Immutable once created; a "restore" creates a new row rather than changing an old one.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can go from "no architecture overview" to "image visible on the SSP page" in a single upload action.
- **SC-002**: 100% of non-image or oversized upload attempts are rejected before anything is written to the database — verified by a pytest test, not manual inspection.
- **SC-003**: After a restore action, the SSP overview page immediately shows the restored image as current, and the version history shows one additional entry (the restore) rather than a mutated old entry.

## Design Notes (implementation grounding)

- **Model** (`scaffold/apps/ssp/models.py`, alongside `SSPlan` and its other children):
  - `SSPArchitectureOverview` — `id`, `ssp_id` (FK → `ssp_plans.id`, cascade delete), `version_number` (int, per-SSP incrementing, e.g. via `func.max(version_number)+1` at insert time within the same transaction), `image_data` (`db.LargeBinary`), `mime_type` (`image/png` / `image/jpeg`), `original_filename`, `file_size_bytes`, `uploaded_by_id` (FK → users, nullable `SET NULL`), `uploaded_at`.
  - Relationship on `SSPlan`: `architecture_overview_versions` (`cascade="all, delete-orphan"`, `order_by="SSPArchitectureOverview.version_number.desc()"`), mirroring `adr_records`.
- **Validation**: reuse Pillow (check if already a dependency; if not, verify with `imghdr`-equivalent or Pillow's `Image.open(...).verify()`) to confirm the upload is a genuine PNG/JPEG before storing, plus a `FileSize`/content-length check for the 5 MB cap — form-level via `flask_wtf.file.FileField` + `FileAllowed(["png", "jpg", "jpeg"])`, matching the `PrincipleImportForm`/`ControlImportForm` pattern from the ADR feature above.
- **Routes** (`scaffold/apps/ssp/routes.py`):
  - `POST /ssp/<ssp_id>/architecture-overview` — upload a new version (computes next `version_number`, stores, logs, redirects to `ssp.view`).
  - `GET /ssp/<ssp_id>/architecture-overview/<version_id>/image` — streams the stored bytes with `current_app.response_class(data, mimetype=...)` (or `send_file(BytesIO(...), mimetype=...)`), used both for the current image `<img src>` and history thumbnails.
  - `POST /ssp/<ssp_id>/architecture-overview/<version_id>/restore` — loads that version's bytes/mime/filename, inserts a new version row with them, logs the restore (including `restored_from_version=<n>` in the audit details), redirects to `ssp.view`.
- **Template** (`scaffold/apps/ssp/templates/ssp/view.html`): current image block near the overview fields, plus a collapsible "Version history" list (thumbnail or filename + uploader + date + "Restore" button per past version, no button on the current one).
- **Migration**: new Alembic revision for `ssp_architecture_overview_versions`, following the naming convention of the ADR feature's migrations above.

## Open Questions

- **Resolved**: whether restore rewrites history vs. appends — appends (copy-forward), per the scope-challenge discussion; keeps the table append-only and avoids a fragile "current" flag.
- **Out of scope**: multi-image overviews (e.g. separate network diagram + data-flow diagram) — this feature is exactly one image stream per SSP. Extending to multiple named diagram slots is a natural follow-up if requested, not assumed here.
- **Out of scope**: including the architecture overview image in the SSP PDF export (`ssp.export_pdf`) — a reasonable follow-up, but not required for this feature to deliver value on the web view, and deferred rather than assumed.
