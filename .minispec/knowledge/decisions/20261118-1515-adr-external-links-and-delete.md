---
type: decision
id: 20261118-1515-adr-external-links-and-delete
date: 2026-11-18
status: accepted
supersedes: null
superseded_by: null
impacts:
  - scaffold/apps/ssp/models.py
  - scaffold/apps/ssp/forms.py
  - scaffold/apps/ssp/routes.py
  - scaffold/apps/ssp/templates/ssp/adrs.html
  - scaffold/apps/ssp/templates/ssp/add_adr.html
  - scaffold/apps/ssp/templates/ssp/edit_adr.html
  - scaffold/apps/ssp/templates/ssp/adr_detail.html
  - scaffold/apps/ssp/templates/ssp/view.html
  - scaffold/apps/ssp/templates/ssp/print.html
  - migrations/versions/*
tags: [ssp, adr, external-link, delete]
participants: [Ferry Stelte, Claude]
---

# ADRs: security-only scope, external links (SSP register and per ADR), deletable

Builds on `20260829-1011-adr-principle-catalogue-design`. The principle
catalogue, status transitions and supersession are unchanged.

## Context

Teams already describe ADRs elsewhere, for example on Confluence. Re-typing
them in the app is duplicate work. Users also cannot delete an ADR, and it is
unclear that only security-related ADRs belong in the SSP.
`ADRRecord.supersedes_id` is a self-FK without `ondelete`, so a delete inside a
supersession chain needs a rule.

## Options Considered

- Link: SSP-level register URL / per-ADR link / both.
- Delete: unlink-and-restore / block when in a chain.

## Decision

**External links: both levels.**
- `SSPlan.adr_register_url` (String 500, nullable, absolute http(s) URL) is
  edited in the SSP metadata form. It is shown as "ADR register" at the top of
  the ADR list and in the SSP view ADR section. The print export shows it as
  URL text.
- `ADRRecord.external_url` (String 500, nullable, absolute http(s) URL) is an
  optional field on the create and edit forms.
- `ADRRecord.context` and `decision` become nullable (migration). Form rule:
  either `external_url` is set, or both context and decision are filled. This
  makes a lightweight ADR possible: title, primary principle, status and link.
- The detail page shows "Described externally → link" when `external_url` is
  set, and the context/decision blocks only when they have content.

**Delete: unlink and restore.**
- `POST /ssp/<id>/adrs/<adr_id>/delete` needs a confirm prompt and is available
  to any logged-in user, like editing an ADR. Within one transaction:
  - if the ADR supersedes another one (`supersedes_id`), the predecessor goes
    back to its `status_before_supersede`, or to `accepted` when that is NULL
    (audit `adr_unsuperseded`; amended by 20261118-1530, CHK001);
  - if a successor supersedes this ADR, the successor's `supersedes_id` is
    cleared;
  - secondary-principle links are removed through the existing M2M cascade;
  - audit `adr_deleted` with title, status and ssp_id.

**Security-only scope (copy only).** Every ADR surface uses the label "Security
ADRs" and gets an intro line: "Record only security-relevant architecture
decisions for this system." The form gets help text with examples.

## Consequences

### Positive
- ✅ Teams can point to their existing ADR documentation instead of copying it
- ✅ Mistaken ADRs can be removed without breaking supersession integrity

### Negative
- ❌ The app does not check that external links still resolve
- ❌ A deleted ADR is gone (the audit trail keeps title and status)
