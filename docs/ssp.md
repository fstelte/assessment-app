# System Security Plan (SSP)

The SSP module (`/ssp`) holds one System Security Plan per BIA context
(system), structured after NIST SP 800-18. This guide covers the parts that
users maintain by hand. The implementation background is in
`docs/ssp_implementation_plan.md`.

## Access

Any signed-in user can view and edit an SSP, including deleting
interconnections, POA&M items, architecture overview versions and ADRs.
Every delete asks for confirmation and is written to the audit log with the
user who did it. The SSP lists (laws/regulations/policies and monitoring
frequencies) are maintained by administrators only.

## Metadata (Edit SSP)

**Edit SSP** on the SSP page holds the authorization boundary, the laws and
regulations, the plan dates, continuous monitoring and the ADR register link.

- **Laws, regulations & policies** is a multi-select from the list that
  administrators maintain (see [SSP lists](#ssp-lists-administrators)). Hold
  Ctrl (Cmd on Mac) to select several.
- **Review frequency** (continuous monitoring) is a single choice from the
  same admin-managed lists.
- An option that an administrator deactivates stays on the SSPs that already
  use it. On the edit page it is labelled "(inactive)", and it is no longer
  offered for new selections.
- The C/I/A impact levels are always derived from the BIA consequences and
  cannot be overridden on the SSP.

## Continuous monitoring

Continuous monitoring describes how **progress on this SSP** is tracked: which
KPIs and KRIs are measured, what is monitored, who does it, with which tools
and how often.

## Interconnections (section 11)

The systems this system connects to come from the **interfaces recorded in
the BIA** (the BIA's *Interfaces* field: one system per line, or separated by
`;`). The SSP adds them automatically whenever it is opened, edited or
exported. You record the details per system: owning organisation, agreement
type, data direction, security contact and notes.

- Rows from the BIA show a **BIA** badge. Their name comes from the BIA and
  cannot be changed on the SSP; change it in the BIA instead.
- Names are matched without regard to case or extra spaces, so `HR System`
  and `hr  system` are the same system.
- When a system is removed from the BIA, its row stays (with your details)
  and shows **No longer in BIA**, or "(no longer in BIA)" in the export.
  Delete it once you have checked it.
- A row that is still in the BIA cannot be deleted, because it would come
  straight back. Remove it from the BIA interfaces first.
- You can add systems that are not in the BIA. If such a system is later
  added to the BIA, the existing row becomes a BIA row and keeps its details.
- Renaming an interface in the BIA creates a new row and marks the old one as
  no longer in the BIA. Copy the details across and delete the old row.

## Architecture overview

Upload the architecture diagram on the SSP page.

- **Accepted:** PNG, JPEG or PDF, at most 10 MB. Images can be at most
  8000×8000 pixels. Export Visio, draw.io or SVG diagrams as PNG or PDF
  first.
- If an upload is refused, the message names the reason: wrong file type, not
  a valid image or PDF, too large, or too many pixels.
- Images are shown on the page. PDFs are shown as a card with **Download
  PDF**; they are downloaded rather than opened inside the application.
- Each upload is a new version. Older versions are under **Version history**,
  where you can **Restore** one (it becomes the newest version) or
  **Delete** it. Deleting the current version makes the previous one current.
  Deleting the only version leaves the SSP without an overview.

Uploads larger than 1 MB need the gateway's `client_max_body_size` to be set
(see `docs/deployment.md`, "Upload size limit").

## POA&M

The Plan of Action and Milestones is used to **steer and monitor improvements
to the system described in the plan**. Record each weakness in the SSP and
track the detailed work in Jira.

- A POA&M item needs a weakness description and a status. Add the **Jira
  link** (`http://` or `https://`) to the issue or epic where the work is
  tracked. It appears on the POA&M list, the SSP page and the export.
- Point of contact, scheduled completion, resources and estimated cost are
  optional, under **Details (optional)**. Milestones are optional too. Both
  sections open automatically when they contain data.

## Security ADRs

Record only **security-relevant** architecture decisions for the system, for
example authentication, encryption, network segmentation or logging. Every
ADR is anchored to an architecture principle that administrators maintain.

- **ADR register:** on **Edit SSP**, add a link to the page where the
  system's security decisions are documented (for example Confluence). It is
  shown on the ADR list, the SSP page and the export.
- **Link per ADR:** an ADR can point to its external description with **Link
  to ADR description**. With a link, Context and Decision are optional;
  without one, both are required.
- **Delete:** an ADR can be deleted from its detail page or the ADR list. If
  it had replaced (superseded) another ADR, that ADR gets back the status it
  had before. If a newer ADR had replaced it, that newer ADR simply no longer
  points to it.

## SSP lists (administrators)

**Administration → SSP lists** (`/admin/ssp-options`, linked from the
`/admin/users` page) maintains two lists:

| List | Used for | Selection on the SSP |
|---|---|---|
| Laws, regulations and policies | Section 12 | Several per SSP |
| Monitoring frequencies | Continuous monitoring | One per SSP |

- Names must be unique within a list, regardless of case.
- Options are listed alphabetically.
- **Deactivate** hides an option from new selections. SSPs that use it keep
  it.
- **Delete** removes an option that no SSP uses. An option in use is
  deactivated instead, and the message says how many SSPs use it.
- Every change is recorded in the audit log (`ssp_option_created`,
  `ssp_option_updated`, `ssp_option_toggled`, `ssp_option_deleted`).

## Audit events

| Event | When |
|---|---|
| `ssp_updated` | Metadata saved; includes the selected law and frequency option IDs |
| `ssp_interconnections_reconciled` | BIA interfaces added or adopted as interconnections (`added`, `adopted`) |
| `ssp_architecture_overview_uploaded` / `_restored` / `_deleted` | Architecture overview versions |
| `adr_created` / `adr_status_changed` / `adr_superseded` | ADR changes |
| `adr_deleted` / `adr_unsuperseded` | ADR deleted; the ADR it replaced got its earlier status back |
| `ssp_option_*` | SSP list maintenance (admin) |
