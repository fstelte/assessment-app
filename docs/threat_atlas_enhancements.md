# ThreatAtlas-Inspired Enhancements for the Threat Module

**Reference project**: [OWASP ThreatAtlas](https://github.com/OWASP/www-project-threatatlas)

This document describes features from the OWASP ThreatAtlas project that can be
meaningfully added to the existing `scaffold/apps/threat/` module. Each section
provides context, a concrete implementation plan, and notes on how it fits the
existing codebase conventions.

---

## Current State Summary

The existing threat module already provides:
- STRIDE-LM taxonomy (Spoofing / Tampering / Repudiation / Information Disclosure / Denial of Service / Elevation of Privilege / Lateral Movement)
- `ThreatModel` → `ThreatModelAsset` → `ThreatScenario` hierarchy
- Risk scoring matrix (likelihood × impact, 1-5 scale)
- Residual risk tracking (post-treatment)
- Treatment options (accept / mitigate / transfer / avoid)
- Scenario statuses (identified / analysed / mitigated / accepted / closed)
- CIA impact tagging per scenario
- CSA control linking (M2M to `csa_controls`)
- BIA import (pre-populate assets from BIA components)
- CSV / HTML / PDF export

---

## Feature 1 — Multi-Framework Knowledge Base

### What ThreatAtlas does
ThreatAtlas ships a seeded library of pre-defined threats and mitigations
organised by framework: **STRIDE**, **PASTA**, **OWASP Top 10 (2021)**,
**LINDDUN**. Each entry has a `name`, `description`, `category`, and
`is_custom` flag. Users can browse, search, and attach knowledge-base threats
to diagram elements, or add their own custom entries.

### Why it is valuable here
Currently, every `ThreatScenario` is created from scratch. A reusable library
of known threats per STRIDE category (and beyond) would speed up modelling and
improve consistency across teams.

### Implementation plan

#### 1a. New models (`scaffold/apps/threat/models.py`)

```python
class ThreatFramework(db.Model, TimestampMixin):
    __tablename__ = "threat_frameworks"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # e.g. "STRIDE", "OWASP Top 10"
    description = db.Column(db.Text)
    is_builtin = db.Column(db.Boolean, default=True)
    entries = db.relationship("ThreatLibraryEntry", back_populates="framework", cascade="all, delete-orphan")


class ThreatLibraryEntry(db.Model, TimestampMixin):
    __tablename__ = "threat_library_entries"
    id = db.Column(db.Integer, primary_key=True)
    framework_id = db.Column(db.Integer, db.ForeignKey("threat_frameworks.id"), nullable=False)
    framework = db.relationship("ThreatFramework", back_populates="entries")
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))       # e.g. "Spoofing", "Broken Access Control"
    suggested_mitigation = db.Column(db.Text)
    is_custom = db.Column(db.Boolean, default=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
```

Add a FK on `ThreatScenario` to optionally link back to the library entry it
was created from:

```python
# In ThreatScenario
library_entry_id = db.Column(db.Integer, db.ForeignKey("threat_library_entries.id"), nullable=True)
library_entry = db.relationship("ThreatLibraryEntry")
```

#### 1b. Seed script (`scaffold/scripts.py` or a new CLI command)

Register a Flask CLI command `seed-threat-library` that inserts the four
built-in frameworks with their threats and mitigations on first run (idempotent
via `get_or_create`). Source data should live in
`scaffold/apps/threat/data/library.json` so it can be updated without touching
Python. Use the full STRIDE, OWASP Top 10, PASTA, and LINDDUN datasets from
the ThreatAtlas seed scripts as the starting point.

#### 1c. Routes (`scaffold/apps/threat/routes.py`)

| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/threat/library/` | Browse all frameworks |
| GET | `/threat/library/<fw_id>/` | List entries for a framework; supports `?q=` search and `?category=` filter |
| GET/POST | `/threat/library/<fw_id>/new` | Add a custom entry |
| GET/POST | `/threat/library/entries/<eid>/edit` | Edit a custom entry |
| POST | `/threat/library/entries/<eid>/delete` | Delete a custom entry (custom only) |
| POST | `/threat/<model_id>/scenarios/new-from-library/<eid>` | Pre-populate new scenario form from a library entry |

#### 1d. Scenario form changes (`scaffold/apps/threat/forms.py`)

Add an optional `library_entry_id` hidden field to `ThreatScenarioForm`. When
the "new-from-library" route is hit, render the standard `scenario_form.html`
with fields pre-filled from the library entry (title, description, suggested
mitigation, STRIDE category mapping).

#### 1e. Templates

- `threat/library/index.html` — framework cards, search bar
- `threat/library/entries.html` — filterable table with Add / Edit / Delete actions
- Extend `threat/scenario_form.html` with a "Pick from library" button that
  opens a modal (`threat/library/_modal.html`) using Bootstrap offcanvas or a
  regular modal; on selection, fills the form via JavaScript fetch to
  `/threat/library/entries/<eid>/json`.

#### Migration

```
poetry run flask --app scaffold:create_app db migrate -m "add threat library models"
poetry run flask --app scaffold:create_app db upgrade
```

---

## Feature 2 — PASTA Framework Support

### What ThreatAtlas does
PASTA (Process for Attack Simulation and Threat Analysis) adds a second
analytical lens to complement STRIDE. ThreatAtlas seeds 10 PASTA-specific
threats (API-centric) and 10 mitigations covering attack surface analysis,
threat analysis, and vulnerability analysis.

### Why it is valuable here
The DPIA/FRIA module already processes privacy risks; PASTA's business-impact
orientation (it starts from business objectives) aligns well with BIA data
already in the platform.

### Implementation plan

- PASTA is covered by Feature 1's `ThreatFramework` / `ThreatLibraryEntry`
  models — no extra model work needed.
- Extend the `StrideCategory` enum OR add a separate `FrameworkCategory` field
  on `ThreatScenario` so scenarios can be tagged to a PASTA stage
  (Asset Analysis / Attack Surface Analysis / Attack Modeling / Threat Analysis /
  Vulnerability Analysis / Attack / Impact Analysis). The simplest approach:

```python
# In ThreatScenario
methodology = db.Column(db.String(50), default="STRIDE")  # "STRIDE" | "PASTA" | "LINDDUN" | "OWASP"
pasta_stage  = db.Column(db.String(50), nullable=True)     # only set when methodology == "PASTA"
```

- The `scenario_form.html` should conditionally show the PASTA stage dropdown
  when the user selects "PASTA" as methodology (JavaScript show/hide).
- The `model_detail.html` scenario list should group by `methodology` then
  `stride_category` / `pasta_stage`.

---

## Feature 3 — LINDDUN Privacy Threat Framework

### What ThreatAtlas does
LINDDUN covers seven privacy threat categories: Linkability, Identifiability,
Non-repudiation, Detectability, Disclosure of Information, Unawareness,
Non-compliance. ThreatAtlas seeds threats and mitigations for all seven.

### Why it is valuable here
This application already has a DPIA/FRIA module. LINDDUN threats are directly
relevant to data protection assessments. A `ThreatModel` created in the context
of a DPIA could automatically suggest LINDDUN scenarios.

### Implementation plan

- Covered by the library framework (Feature 1).
- Add a `suggested_frameworks` column on `ThreatModel` (JSON array, e.g.
  `["STRIDE", "LINDDUN"]`) that pre-filters the library modal.
- In the `model_new` route, detect if the model is linked to a DPIA
  (`dpia_id` FK, optional) and pre-select LINDDUN.

Optional DPIA link:

```python
# In ThreatModel
dpia_id = db.Column(db.Integer, db.ForeignKey("dpia_assessments.id"), nullable=True)
dpia = db.relationship("DpiaAssessment", backref="threat_models")
```

---

## Feature 4 — OWASP Top 10 Framework

### What ThreatAtlas does
Seeds 36 threats and mitigations mapped to all 10 OWASP 2021 categories
(Broken Access Control, Cryptographic Failures, Injection, Insecure Design,
Security Misconfiguration, Vulnerable Components, Authentication Failures,
Integrity Failures, Logging Failures, SSRF).

### Why it is valuable here
When threat-modelling web applications, teams need OWASP Top 10 coverage.
The existing STRIDE categories partially overlap but do not map 1:1.

### Implementation plan

- Covered by Feature 1's library framework.
- Map each OWASP category to the closest STRIDE category as a `stride_hint`
  field on `ThreatLibraryEntry` (optional, for display only):

| OWASP category | STRIDE hint |
|---|---|
| Broken Access Control | ELEVATION_OF_PRIVILEGE |
| Cryptographic Failures | INFORMATION_DISCLOSURE |
| Injection | TAMPERING |
| Insecure Design | TAMPERING |
| Security Misconfiguration | INFORMATION_DISCLOSURE |
| Vulnerable Components | TAMPERING |
| Authentication Failures | SPOOFING |
| Integrity Failures | TAMPERING |
| Logging Failures | REPUDIATION |
| SSRF | INFORMATION_DISCLOSURE |

---

## Feature 5 — Interactive Data Flow Diagram (DFD) Canvas

### What ThreatAtlas does
ThreatAtlas renders an interactive DFD canvas (ReactFlow) where users drag
process nodes, data stores, external entities, and trust boundary boxes and
draw data-flow edges. Threats are attached directly to nodes and edges.

### Why it is valuable here
Currently, assets are a flat list with an `asset_type` enum
(component / data_flow / trust_boundary / external_entity / data_store).
There is no visual layout. A DFD canvas would greatly improve usability for
complex systems.

### Implementation plan

This is the most significant UI feature. Approach with progressive enhancement:

#### Phase A — Position persistence (low effort)
Add `x_pos` / `y_pos` / `width` / `height` float columns to
`ThreatModelAsset`. Provide a simple drag-and-drop grid view in
`model_detail.html` using [Interact.js](https://interactjs.io/) (CDN, no npm
required) that saves positions via a PATCH endpoint:

```
PATCH /threat/<model_id>/assets/<aid>/position
Body: {"x": 120.5, "y": 340.0}
```

#### Phase B — SVG diagram export
Add a "Download diagram" button that uses the browser's `Canvas` or
`SVGElement.outerHTML` to produce an SVG of the asset layout, without
requiring a server-side rendering step.

#### Phase C — Full DFD canvas (high effort, optional)
If a richer experience is required, embed a lightweight JS diagramming
library such as [Drawflow](https://github.com/jerosoler/Drawflow) (MIT, single
JS file) into `model_detail.html`. Persist the diagram JSON in a `diagram_data`
Text column on `ThreatModel`. Provide a Flask route:

```
GET/PUT /threat/<model_id>/diagram
```

This avoids introducing React/TypeScript build tooling into the Flask project.

---

## Feature 6 — Products Grouping (multi-model product hierarchy)

### What ThreatAtlas does
Introduces a `Product` entity that groups multiple diagrams (threat models)
under one product/system. The dashboard shows threat counts per product.

### Why it is valuable here
Currently, all threat models are top-level. For organisations with many
systems, a product grouping would allow scoped reporting.

### Implementation plan

Add a `ThreatProduct` model:

```python
class ThreatProduct(db.Model, TimestampMixin):
    __tablename__ = "threat_products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    is_archived = db.Column(db.Boolean, default=False)
    models = db.relationship("ThreatModel", back_populates="product")
```

Add `product_id` FK (nullable) to `ThreatModel` so existing models are
unaffected.

Routes:

| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/threat/products/` | List all products |
| GET/POST | `/threat/products/new` | Create a product |
| GET | `/threat/products/<pid>/` | Product detail: list models + summary stats |
| GET/POST | `/threat/products/<pid>/edit` | Edit |
| POST | `/threat/products/<pid>/archive` | Archive |

The existing `/threat/` dashboard remains unchanged; the product dashboard is
additive.

---

## Feature 7 — Threat Status Lifecycle Enhancements

### What ThreatAtlas does
Mitigations have their own status: `Proposed → Implemented → Verified`.
This is separate from the scenario status.

### Why it is valuable here
The current `ThreatScenario` model has a single `status` field
(identified / analysed / mitigated / accepted / closed) and a free-text
`mitigation` field. There is no way to track whether a mitigation has been
verified.

### Implementation plan

Add a `ThreatMitigationAction` model for structured mitigation tracking,
separate from the library link:

```python
class MitigationStatus(enum.Enum):
    PROPOSED    = "proposed"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    VERIFIED    = "verified"

class ThreatMitigationAction(db.Model, TimestampMixin):
    __tablename__ = "threat_mitigation_actions"
    id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey("threat_scenarios.id"), nullable=False)
    scenario = db.relationship("ThreatScenario", backref="mitigation_actions")
    library_entry_id = db.Column(db.Integer, db.ForeignKey("threat_library_entries.id"), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.Enum(MitigationStatus), default=MitigationStatus.PROPOSED)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text)
```

Expose inline CRUD for mitigation actions inside `scenario_detail.html`
using simple Bootstrap card components + a small HTMX or fetch-based partial,
consistent with the existing pattern in the CSA module.

---

## Feature 8 — Dashboard Enhancements

### What ThreatAtlas does
The dashboard aggregates all threats across all products/diagrams with filters
for severity, status, product, and diagram. Threat cards show a colored
severity stripe.

### Why it is valuable here
The existing `/threat/` dashboard just lists models. There is no cross-model
scenario summary.

### Implementation plan

Extend the `threat.dashboard` route to pass aggregated scenario statistics:

```python
# In routes.py — dashboard view
stats = {
    "total": ThreatScenario.query.filter_by(is_archived=False).count(),
    "by_level": db.session.query(
        ThreatScenario.risk_level, db.func.count()
    ).filter_by(is_archived=False).group_by(ThreatScenario.risk_level).all(),
    "by_status": db.session.query(
        ThreatScenario.status, db.func.count()
    ).filter_by(is_archived=False).group_by(ThreatScenario.status).all(),
    "open_critical": ThreatScenario.query.filter_by(
        risk_level=RiskLevel.CRITICAL, is_archived=False
    ).filter(ThreatScenario.status != ScenarioStatus.CLOSED).count(),
}
```

Add a dedicated "All Threats" tab or section to `threat/dashboard.html` showing
a filterable scenario list across all models (search, severity filter, status
filter). Use Bootstrap 5 collapse / tab components — no new JS needed.

---

## Feature 9 — Custom Threat / Mitigation Entries (user-owned)

### What ThreatAtlas does
Users can add custom threats and mitigations to any framework. Custom entries
are flagged with `is_custom=True` and an owner reference so only the owner or
admin can edit/delete them.

### Why it is valuable here
Organisations have domain-specific threats not covered by STRIDE/OWASP. The
existing `ThreatLibraryEntry` model (Feature 1) already has `is_custom` and
`created_by_id`. The routes for `/threat/library/<fw_id>/new` and edit/delete
should enforce this ownership check — consistent with the existing access
control patterns in the codebase.

### Implementation plan

In the library routes:

```python
# edit / delete guard
entry = ThreatLibraryEntry.query.get_or_404(eid)
if not entry.is_custom:
    abort(403)
if entry.created_by_id != current_user.id and not current_user.has_role("ROLE_ADMIN"):
    abort(403)
```

No additional model changes beyond Feature 1.

---

## Implementation Order (Recommended)

| Priority | Feature | Effort | Value |
|----------|---------|--------|-------|
| 1 | Feature 1 — Knowledge Base (STRIDE + OWASP Top 10) | Medium | High |
| 2 | Feature 8 — Dashboard aggregation | Low | High |
| 3 | Feature 7 — Mitigation action tracking | Medium | High |
| 4 | Feature 4 — OWASP Top 10 seed data | Low (data only) | Medium |
| 5 | Feature 2 — PASTA methodology | Low | Medium |
| 6 | Feature 3 — LINDDUN + DPIA link | Medium | Medium |
| 7 | Feature 6 — Product grouping | Medium | Medium |
| 8 | Feature 5A — DFD position persistence | Low | Low |
| 9 | Feature 5B/C — Full DFD canvas | High | Low–Medium |
| 10 | Feature 9 — Custom entries | Low (built into F1) | Medium |

---

## General Coding Notes for the Coding Assistant

- Follow the existing Flask Blueprint pattern in `scaffold/apps/threat/`.
- All new models must extend `TimestampMixin` from `scaffold.apps.identity.models`.
- All new routes require `@login_required` and `role_required("ROLE_ADMIN",
  "ROLE_ASSESSMENT_MANAGER")` consistent with the existing threat routes.
- All user-visible strings must be wrapped in `_()` / `lazy_gettext` from
  `scaffold.core.i18n` and translation keys added to
  `scaffold/translations/en.json` (and `nl.json`).
- All mutating actions must call `core.audit.log_event()` with the appropriate
  `entity_type` and `entity_id`.
- After adding models, always generate a migration:
  ```
  poetry run flask --app scaffold:create_app db migrate -m "<description>"
  poetry run flask --app scaffold:create_app db upgrade
  ```
- Use `Flask-WTF` forms for all user-facing forms; CSRF is enabled in
  production.
- Templates go in `scaffold/apps/threat/templates/threat/` and extend
  `base.html`.
- Use Bootstrap 5 classes first; Tailwind utility classes only as a supplement.
- Write `pytest` tests in `tests/test_threat_routes.py` for new routes,
  using the `client` fixture from `tests/conftest.py`.
