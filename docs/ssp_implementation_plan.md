# System Security Plan (SSP) — Implementation Plan
## Based on NIST SP 800-18 Rev 1

---

## Overview

This document describes the plan to implement a **System Security Plan (SSP)** module in the assessment platform, conforming to NIST SP 800-18 Rev 1 ("Guide for Developing Security Plans for Federal Information Systems").

### Key decisions

| Question | Decision |
|---|---|
| Anchor entity | One SSP per `ContextScope` (BIA system) |
| Output | Editable online view (HTML) + PDF export |
| Authorizing Official | Not required |
| ISSO | Maps to `ContextScope.security_manager` |
| Contact details | Name + email only (from existing user fields) |
| System abbreviation / operational status / system type | New fields added to `ContextScope` |
| FIPS 199 C/I/A rating | Auto-derived from BIA Consequences, with manual override on the SSP |
| Physical environments / dependencies | Auto-populated from BIA `Component` dependency fields |
| Laws / Regulations / Policies | Free-text editable list on the SSP |
| Section 13 security controls | Controls linked via Threat Model scenarios and Risk register for the ContextScope's components |
| System interconnections | Auto-populated from `ContextScope.interfaces`, editable per-entry on the SSP |
| Module location | New dedicated module: `scaffold/apps/ssp/` |

---

## NIST SP 800-18 Section Mapping

| SP 800-18 Section | Source in App |
|---|---|
| 1. System Name | `ContextScope.name` |
| 2. System Abbreviation | `ContextScope.abbreviation` *(new field)* |
| 3. Responsible Organization | `ContextScope.responsible` |
| 4. System Owner | `ContextScope.author` → `User.first_name + last_name`, `email` |
| 5. Other Designated Contacts | `ContextScope`: `project_leader`, `risk_owner`, `product_owner`, `technical_administrator`, `security_manager`, `incident_contact` |
| 6. ISSO | `ContextScope.security_manager` |
| 7. Operational Status | `ContextScope.operational_status` *(new field)*: Operational / Under Development / Major Modification |
| 8. System Type | `ContextScope.system_type` *(new field)*: Major Application / General Support System |
| 9. General Description/Purpose | `ContextScope.service_description` + `scope_description` |
| 10. System Environment | Aggregated from `Component.dependencies_it_systems_applications`, `dependencies_equipment`, `dependencies_suppliers`, `dependencies_facilities`, `dependencies_others` |
| 11. System Interconnections | Auto-populated from `ContextScope.interfaces`; stored as editable `SSPInterconnection` rows |
| 12. Laws / Regulations / Policies | `SSPlan.laws_regulations` — free text |
| 13. Security Categorization (FIPS 199) | Derived from `Consequences` (CIA, worst-case), with `SSPlan.fips_*_override` fields allowing Low/Moderate/High manual override |
| 14. Minimum Security Controls | `Control` objects linked via `ThreatScenario.controls` and `Risk.controls` for components of the ContextScope; implementation statement stored in `SSPControlEntry` |
| 15. Plan Completion Date | `SSPlan.plan_completion_date` |
| 16. Plan Approval Date | `SSPlan.plan_approval_date` |

---

## New Module Structure

```
scaffold/apps/ssp/
├── __init__.py          # Blueprint definition + NAVIGATION entry
├── models.py            # SSPlan, SSPInterconnection, SSPControlEntry
├── routes.py            # All SSP routes
├── forms.py             # SSPEditForm, SSPInterconnectionForm, SSPControlEntryForm
├── services.py          # Query helpers (gather controls, derive FIPS, build env summary)
└── templates/
    └── ssp/
        ├── index.html       # List all SSPs with their ContextScope names
        ├── view.html        # Full NIST SP 800-18 read-only view
        ├── edit.html        # Edit SSP-specific metadata fields
        ├── interconnections.html  # Manage interconnection table entries
        ├── controls.html    # Review and edit Section 13 control entries
        └── print.html       # Print/PDF-optimised layout (no navigation)
```

---

## Implementation Phases

### Phase 1 — Database Models & Migration

**Changes to `ContextScope` (BIA):**

Add three new columns:
- `abbreviation` (String 50, nullable) — short identifier, e.g. "HRMS"
- `operational_status` (Enum: `operational` / `under_development` / `major_modification`, nullable)
- `system_type` (Enum: `major_application` / `general_support_system`, nullable)

**New models in `scaffold/apps/ssp/models.py`:**

```
SSPlan
  id                  Integer PK
  context_scope_id    Integer FK bia_context_scope (unique — one SSP per scope)
  laws_regulations    Text (nullable)
  authorization_boundary  Text (nullable)
  fips_confidentiality    Enum(low/moderate/high/not_set)  default not_set
  fips_integrity          Enum(low/moderate/high/not_set)  default not_set
  fips_availability       Enum(low/moderate/high/not_set)  default not_set
  plan_completion_date    Date (nullable)
  plan_approval_date      Date (nullable)
  created_at          DateTime
  updated_at          DateTime
  created_by_id       Integer FK users.id

SSPInterconnection
  id                  Integer PK
  ssp_id              Integer FK ssp_plans.id
  system_name         String 255
  owning_organization String 255
  agreement_type      Enum(mou/isa/contract/informal/none)
  data_direction      Enum(incoming/outgoing/bidirectional)
  security_contact    String 255
  notes               Text
  sort_order          Integer default 0

SSPControlEntry
  id                      Integer PK
  ssp_id                  Integer FK ssp_plans.id
  control_id              Integer FK csa_controls.id
  implementation_status   Enum(planned/partially_implemented/implemented/not_applicable)  default planned
  responsible_entity      String 255
  implementation_statement  Text
  source                  Enum(threat/risk/manual)
```

**Migration:** `poetry run flask --app scaffold:create_app db migrate -m "add ssp module"`

---

### Phase 2 — BIA Form Updates

Update `scaffold/apps/bia/forms.py` (`ContextScopeForm`) to include:
- `abbreviation` — `StringField`, max 50 chars, optional
- `operational_status` — `SelectField` with choices: operational / under_development / major_modification
- `system_type` — `SelectField` with choices: major_application / general_support_system

Update the BIA edit template to render these three new fields.

---

### Phase 3 — SSP Blueprint & Core Routes

Register `scaffold.apps.ssp` in `scaffold/config.py` `_DEFAULT_MODULES`.

Routes:

| Method | URL | Description |
|---|---|---|
| GET | `/ssp/` | List all SSPs (index) |
| GET/POST | `/ssp/create/<context_scope_id>` | Create an SSP for a ContextScope (if one does not exist) |
| GET | `/ssp/<ssp_id>` | View full NIST SP 800-18 SSP |
| GET/POST | `/ssp/<ssp_id>/edit` | Edit SSP metadata (laws, dates, FIPS overrides, boundary) |
| GET/POST | `/ssp/<ssp_id>/interconnections` | Manage interconnection table |
| GET/POST | `/ssp/<ssp_id>/controls` | Review and annotate Section 13 control entries |
| GET | `/ssp/<ssp_id>/export/pdf` | Stream PDF download |

On POST to `/ssp/create/<context_scope_id>`:
1. Create `SSPlan` record.
2. Call `services.seed_interconnections(ssp)` — parse `ContextScope.interfaces` into `SSPInterconnection` rows.
3. Call `services.seed_controls(ssp)` — gather all `Control` objects linked through ThreatScenario and Risk for the scope's components; create `SSPControlEntry` rows (deduplicated by `control_id`).

---

### Phase 4 — Services Layer (`services.py`)

**`derive_fips_rating(consequences: list[Consequences]) -> dict`**

Map BIA Consequences `consequence_worstcase` scale to FIPS 199 rating:
- Negligible / Low / Minor → Low
- Moderate → Moderate  
- Significant / Severe / Catastrophic → High

Return `{"confidentiality": ..., "integrity": ..., "availability": ...}` taking the highest rating found for each CIA property.

**`seed_interconnections(ssp: SSPlan) -> None`**

Parse `ssp.context_scope.interfaces` (newline/semicolon-separated free text) into rough `SSPInterconnection` rows with `system_name` set and all other fields left blank for the user to complete.

**`seed_controls(ssp: SSPlan) -> None`**

For each `Component` in the ContextScope:
1. Collect `ThreatScenario.controls` from all `ThreatModel` objects where `ThreatModel` → `ThreatModelAsset` → `Component` (via product or direct link — check the actual model relationships).
2. Collect `Control` objects from `Risk.controls` for risks linked to the component.
3. Deduplicate by `control_id`.
4. Create one `SSPControlEntry` per control with `source=threat` or `source=risk`.

**`build_environment_summary(context_scope: ContextScope) -> list[dict]`**

Aggregate all `Component` dependency fields into a structured list of `{"component": name, "category": ..., "items": [...]}` for rendering in Section 10.

---

### Phase 5 — SSP View Template (`view.html`)

The view template renders all 16 sections of the SSP as a single scrollable page, using the `view.html` from `incident` as a style reference. Use Tailwind CSS throughout.

Sections:
1. Cover block — system name, abbreviation, org, status, type, dates
2. System Owner & Contacts table
3. General Description / Purpose
4. System Environment — table built from `build_environment_summary()`
5. System Interconnections — table from `ssp.interconnections`
6. Laws / Regulations / Policies — rendered from `ssp.laws_regulations`
7. Security Categorization (FIPS 199) — show derived + override values with traffic-light badges
8. BIA Tier + Criticality summary
9. DPIA summary (if a `DPIAAssessment` exists for any component)
10. Risk Register summary — count by severity
11. Minimum Security Controls — `ssp.control_entries` grouped by CSA control domain
12. Plan Dates + Approval

---

### Phase 6 — Edit Forms & Templates

**`SSPEditForm`** fields:
- `laws_regulations` — `TextAreaField`
- `authorization_boundary` — `TextAreaField`
- `fips_confidentiality`, `fips_integrity`, `fips_availability` — `SelectField` with `[("not_set", "Use derived"), ("low", "Low"), ("moderate", "Moderate"), ("high", "High")]`
- `plan_completion_date`, `plan_approval_date` — `DateField`

**`SSPInterconnectionForm`** fields:
- `system_name`, `owning_organization`, `security_contact` — `StringField`
- `agreement_type` — `SelectField`
- `data_direction` — `SelectField`
- `notes` — `TextAreaField`

**`SSPControlEntryForm`** fields:
- `implementation_status` — `SelectField`
- `responsible_entity` — `StringField`
- `implementation_statement` — `TextAreaField`

---

### Phase 7 — PDF Export

Use the existing `scaffold.core.pdf_export.html_to_pdf_bytes` utility (already used by the incident module).

- Route `/ssp/<ssp_id>/export/pdf` renders `print.html` with `render_template`, passes the HTML through `html_to_pdf_bytes`, and streams the result as `application/pdf`.
- `print.html` is a standalone, navigation-free version of `view.html` with page-break hints (`break-inside-avoid`, `page-break-before: always` on major sections).
- Filename pattern: `ssp_<abbreviation or slug>_<YYYY-MM-DD>.pdf`

---

### Phase 8 — Tests

Add a test file `tests/test_ssp_routes.py` covering:
- SSP creation from a ContextScope
- SSP view renders all expected section headings
- FIPS 199 derivation logic (unit test against `derive_fips_rating`)
- Control seeding populates entries from threat/risk links
- PDF export returns `application/pdf`

---

## File Touch Summary

| File | Action |
|---|---|
| `scaffold/apps/bia/models/__init__.py` | Add 3 fields to `ContextScope` |
| `scaffold/apps/bia/forms.py` | Add 3 fields to `ContextScopeForm` |
| `scaffold/apps/bia/templates/bia/edit_context_scope.html` | Render 3 new fields |
| `scaffold/apps/ssp/__init__.py` | New |
| `scaffold/apps/ssp/models.py` | New |
| `scaffold/apps/ssp/routes.py` | New |
| `scaffold/apps/ssp/forms.py` | New |
| `scaffold/apps/ssp/services.py` | New |
| `scaffold/apps/ssp/templates/ssp/index.html` | New |
| `scaffold/apps/ssp/templates/ssp/view.html` | New |
| `scaffold/apps/ssp/templates/ssp/edit.html` | New |
| `scaffold/apps/ssp/templates/ssp/interconnections.html` | New |
| `scaffold/apps/ssp/templates/ssp/controls.html` | New |
| `scaffold/apps/ssp/templates/ssp/print.html` | New |
| `scaffold/config.py` | Add `scaffold.apps.ssp` to `_DEFAULT_MODULES` |
| `migrations/versions/<hash>_add_ssp_module.py` | Generated by Alembic |
| `tests/test_ssp_routes.py` | New |

---

## Implementation Prompts

The following prompt files drive step-by-step implementation. Run them in order, you can find them under .github/prompts:

1. `ssp-01-models.prompt.md` — Models + migration
2. `ssp-02-bia-fields.prompt.md` — BIA ContextScope field additions
3. `ssp-03-blueprint.prompt.md` — SSP Blueprint, config registration, core routes
4. `ssp-04-services.prompt.md` — Services layer (FIPS derivation, seeding, env summary)
5. `ssp-05-view-template.prompt.md` — Full SSP view template
6. `ssp-06-edit-templates.prompt.md` — Edit forms and edit/interconnections/controls templates
7. `ssp-07-pdf-export.prompt.md` — PDF export route and print template
8. `ssp-08-tests.prompt.md` — Test suite
