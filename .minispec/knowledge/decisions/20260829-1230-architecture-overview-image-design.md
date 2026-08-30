---
type: decision
id: 20260829-1230-architecture-overview-image-design
date: 2026-08-29
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/ssp/models.py
  - scaffold/apps/ssp/routes.py
  - scaffold/apps/ssp/forms.py
  - scaffold/apps/ssp/templates/ssp/view.html
  - migrations/versions/*
tags: [ssp, architecture-overview, file-upload, data-model]
participants: [Ferry Stelte, Claude]
---

# Architecture Overview image on the SSP: DB-blob storage, append-only versioning

## Context

The SSP needed a way to attach a visual architecture overview (a diagram exported as
PNG/JPEG) that's visible directly on the SSP page. Three shape decisions were open:
(1) what content type — file, rich text, or both; (2) where the bytes live, given the
app's Docker deployment has no user-upload volume mounted (only `./backups` and
`./restore`, per `docs/deployment.md`); (3) whether to keep a version history and, if
so, whether "restore" rewrites or appends.

## Decision

1. **Content type**: image upload only (PNG/JPEG), no rich-text description field —
   the user confirmed this is purely a diagram/image use case, not a text-authoring one.
2. **Storage**: the image bytes live in a `db.LargeBinary` column, not on the container
   filesystem. Constitution Principle V ("Operational Readiness Over Local Convenience")
   prohibits local-only shortcuts becoming a hidden production dependency; since no
   upload volume exists today, filesystem storage would silently lose data on container
   recreation unless deployment docs/Compose were also changed. The database is already
   the durable, backed-up store for everything else in this app.
3. **Versioning**: every upload creates a new, immutable, append-only version row, keyed
   by an SSP-scoped incrementing `version_number`. "Current" is simply the highest
   `version_number` for that SSP — there is no separate `is_current` boolean to keep in
   sync (avoids a whole class of "two rows think they're current" bugs).
4. **Restore**: restoring an old version does **not** rewind or mutate history. It reads
   the old version's bytes and inserts them as a **new** version (copy-forward), audit-
   logged with which version it restored from. This mirrors how `ADRRecord` supersession
   already works in this codebase (superseding never edits the old record's core fields,
   it only flips `status` and adds a link) and avoids needing a `restored_from_version_id`
   column — the audit log already captures that relationship.
5. **Permission**: any authenticated user who can reach `ssp.edit` can upload — no new
   role. This matches how the rest of the SSP is edited today (`@login_required` only);
   introducing an admin-only gate here would be inconsistent with every other SSP field.

## Alternatives Considered

- **Filesystem storage under `instance_path`**, like the app's generated PDF/CSV
  exports (`scaffold/apps/incident/routes.py`, `scaffold/apps/bia/routes.py`). Rejected:
  those are regenerable exports, not user-supplied source data: losing them on a
  container restart is a non-event, losing a user's uploaded diagram is not. Would also
  require a new volume mount and deployment doc update (Constitution Principle V
  explicitly calls for the doc update to happen in the same change if this path had
  been chosen).
- **`is_current` boolean flag** instead of "highest version_number wins". Rejected as
  an unnecessary second source of truth — every write would need to flip the old
  current row's flag off in the same transaction, and any bug there silently produces
  zero or two "current" rows.
- **True rollback (edit/reorder existing rows) for restore**. Rejected: breaks the
  append-only/immutable property of the version table, complicates the audit story
  ("why did version 3 become current after version 5 existed"), and isn't needed to
  satisfy the user's actual requirement of "bring an old one back".
- **Rich-text description field alongside the image**. Rejected for this iteration —
  not requested; the SSP already has free-text fields (`authorization_boundary`) that
  can carry prose if needed. Revisit only if a future request specifically asks for a
  written architecture narrative alongside the image.

## Consequences

- One new table (`ssp_architecture_overview_versions`), three new routes (upload,
  serve image, restore), and one template section — no new admin surface, no new role.
- Every version's full image bytes are retained forever (no pruning). Acceptable at the
  5 MB/upload cap for the expected upload frequency (one architecture diagram per SSP,
  updated occasionally); revisit only if this becomes a real storage-growth problem.
- PDF export of the SSP (`ssp.export_pdf`) does not include the architecture overview
  image yet — explicitly deferred, see design.md's Open Questions.
