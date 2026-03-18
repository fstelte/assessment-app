# Threat Modeling Module — Implementation Plan

> STRIDE-LM based threat modeling with exportable threat scenario reports.

---

## 1. Overview

This document describes the plan to add a **Threat Modeling** module to the assessment platform. The module follows the existing architecture: a Flask Blueprint registered via `register()`, SQLAlchemy models with `TimestampMixin`, Flask-WTF forms, Jinja2 templates using Bootstrap 5, and PDF/HTML export via the existing `html_to_pdf_bytes()` pipeline.

### STRIDE-LM Categories

| Category | Code | Description |
|---|---|---|
| Spoofing | S | Impersonating something or someone else |
| Tampering | T | Modifying data or code |
| Repudiation | R | Claiming not to have performed an action |
| Information Disclosure | I | Exposing information to unauthorized parties |
| Denial of Service | D | Blocking access to a service or resource |
| Elevation of Privilege | E | Gaining capabilities without authorization |
| Lateral Movement | LM | Moving through the network after initial foothold |

---

## 2. Data Model

### 2.1 `ThreatModel` — the top-level container

```
threat_models
├── id                  INTEGER PK
├── title               VARCHAR(255) NOT NULL
├── description         TEXT
├── scope               TEXT          — what systems / assets are in scope
├── owner_id            FK → users.id
├── is_archived         BOOLEAN DEFAULT FALSE
├── archived_at         DATETIME
├── created_at          DATETIME
└── updated_at          DATETIME
```

### 2.2 `ThreatModelAsset` — assets within the model (data flows, components, trust boundaries)

```
threat_model_assets
├── id                  INTEGER PK
├── threat_model_id     FK → threat_models.id CASCADE DELETE
├── name                VARCHAR(255) NOT NULL
├── asset_type          ENUM(component, data_flow, trust_boundary, external_entity, data_store)
├── description         TEXT
├── order               INTEGER DEFAULT 0
├── created_at          DATETIME
└── updated_at          DATETIME
```

### 2.3 `ThreatScenario` — the core record, one per identified threat

```
threat_scenarios
├── id                  INTEGER PK
├── threat_model_id     FK → threat_models.id CASCADE DELETE
├── asset_id            FK → threat_model_assets.id SET NULL
├── stride_category     ENUM(spoofing, tampering, repudiation,
│                            information_disclosure, denial_of_service,
│                            elevation_of_privilege, lateral_movement)
├── title               VARCHAR(255) NOT NULL
├── description         TEXT          — full attack scenario narrative
├── threat_actor        VARCHAR(255)  — insider / external / automated
├── attack_vector       TEXT          — how the threat is realized
├── preconditions       TEXT          — what must be true for the threat to apply
├── impact_description  TEXT          — what happens if the threat is realized
├── affected_cia        VARCHAR(3)    — bitmask C/I/A (e.g. "CIA", "CI", "A")
├── likelihood          INTEGER 1-5   — 1 rare … 5 almost certain
├── impact_score        INTEGER 1-5   — 1 negligible … 5 critical
├── risk_score          COMPUTED (likelihood × impact_score, stored)
├── risk_level          ENUM(low, medium, high, critical)
├── treatment           ENUM(accept, mitigate, transfer, avoid)
├── mitigation          TEXT          — controls / countermeasures
├── residual_risk       TEXT
├── status              ENUM(identified, analysed, mitigated, accepted, closed)
├── owner_id            FK → users.id SET NULL
├── is_archived         BOOLEAN DEFAULT FALSE
├── created_at          DATETIME
└── updated_at          DATETIME
```

### 2.4 `ThreatScenarioControl` — links to CSA controls (optional)

```
threat_scenario_controls  (M2M association table)
├── scenario_id         FK → threat_scenarios.id CASCADE DELETE
└── control_id          FK → csa_controls.id CASCADE DELETE
```

### 2.5 Relationships summary

```
ThreatModel  1──*  ThreatModelAsset
ThreatModel  1──*  ThreatScenario
ThreatScenario  *──1  ThreatModelAsset  (nullable, which asset is threatened)
ThreatScenario  *──*  Control           (optional: link to CSA mitigating controls)
ThreatModel / ThreatScenario  *──1  User (owner)
```

---

## 3. Module File Structure

```
scaffold/apps/threat/
├── __init__.py              # register(app), NAVIGATION entry
├── routes.py                # Blueprint bp, all route handlers
├── forms.py                 # Flask-WTF forms
├── models.py                # SQLAlchemy models
├── services.py              # Business logic, risk scoring, export helpers
└── templates/threat/
    ├── dashboard.html        # List of all threat models
    ├── model_detail.html     # Overview of a single ThreatModel + scenarios
    ├── model_form.html       # Create / edit ThreatModel
    ├── asset_form.html       # Add / edit an asset
    ├── scenario_detail.html  # Full detail of one ThreatScenario
    ├── scenario_form.html    # Create / edit scenario (STRIDE-LM picker)
    ├── export_report.html    # Printable / PDF export template
    └── _partials/
        ├── scenario_card.html
        ├── stride_badge.html
        └── risk_matrix.html
```

---

## 4. Routes

All routes are prefixed `/threat/` under the `threat` Blueprint.

| Method | URL | Endpoint | Description |
|---|---|---|---|
| GET | `/threat/` | `threat.dashboard` | List all non-archived threat models |
| GET/POST | `/threat/new` | `threat.model_new` | Create a new ThreatModel |
| GET | `/threat/<id>` | `threat.model_detail` | View ThreatModel + scenario list |
| GET/POST | `/threat/<id>/edit` | `threat.model_edit` | Edit ThreatModel header |
| POST | `/threat/<id>/archive` | `threat.model_archive` | Archive/unarchive |
| GET/POST | `/threat/<id>/assets/new` | `threat.asset_new` | Add an asset |
| GET/POST | `/threat/<id>/assets/<aid>/edit` | `threat.asset_edit` | Edit asset |
| POST | `/threat/<id>/assets/<aid>/delete` | `threat.asset_delete` | Delete asset |
| GET/POST | `/threat/<id>/scenarios/new` | `threat.scenario_new` | Create scenario (STRIDE-LM form) |
| GET | `/threat/<id>/scenarios/<sid>` | `threat.scenario_detail` | View scenario |
| GET/POST | `/threat/<id>/scenarios/<sid>/edit` | `threat.scenario_edit` | Edit scenario |
| POST | `/threat/<id>/scenarios/<sid>/delete` | `threat.scenario_delete` | Delete scenario |
| GET | `/threat/<id>/export/html` | `threat.export_html` | Export as standalone HTML |
| GET | `/threat/<id>/export/pdf` | `threat.export_pdf` | Export as PDF via Playwright |
| GET | `/threat/<id>/export/csv` | `threat.export_csv` | Export scenario CSV |

---

## 5. Forms

### `ThreatModelForm`
- `title` — StringField, required, max 255
- `description` — TextAreaField, optional
- `scope` — TextAreaField, optional (describe the system boundary)

### `ThreatModelAssetForm`
- `name` — StringField, required, max 255
- `asset_type` — SelectField, choices from `AssetType` enum
- `description` — TextAreaField, optional
- `order` — IntegerField, optional, default 0

### `ThreatScenarioForm`
- `stride_category` — SelectField — STRIDE-LM 7-option picker (with visual badges)
- `asset_id` — SelectField, optional, dynamically populated from ThreatModelAsset list
- `title` — StringField, required, max 255
- `description` — TextAreaField, optional
- `threat_actor` — StringField, optional
- `attack_vector` — TextAreaField, optional
- `preconditions` — TextAreaField, optional
- `impact_description` — TextAreaField, optional
- `affected_cia` — MultiCheckboxField (C / I / A)
- `likelihood` — SelectField, 1–5 range
- `impact_score` — SelectField, 1–5 range
- `treatment` — SelectField, 4 options
- `mitigation` — TextAreaField
- `residual_risk` — TextAreaField
- `status` — SelectField, 5 options
- `owner_id` — SelectField, user list

---

## 6. Risk Scoring Logic (`services.py`)

```python
RISK_LEVEL_MATRIX = {
    # (likelihood_band, impact_band) → RiskLevel
    # likelihood bands: low=1-2, medium=3, high=4-5
    # impact bands: low=1-2, medium=3, high=4-5
    ("low",    "low"):    "low",
    ("low",    "medium"): "low",
    ("low",    "high"):   "medium",
    ("medium", "low"):    "low",
    ("medium", "medium"): "medium",
    ("medium", "high"):   "high",
    ("high",   "low"):    "medium",
    ("high",   "medium"): "high",
    ("high",   "high"):   "critical",
}

def compute_risk_score(likelihood: int, impact: int) -> tuple[int, str]:
    score = likelihood * impact          # 1–25
    l_band = "low" if likelihood <= 2 else ("medium" if likelihood == 3 else "high")
    i_band = "low" if impact <= 2 else ("medium" if impact == 3 else "high")
    level = RISK_LEVEL_MATRIX[(l_band, i_band)]
    return score, level
```

`risk_score` and `risk_level` are recalculated and persisted on every save.

---

## 7. Export

### 7.1 PDF (`export_pdf`)
- Renders `export_report.html` with `export_mode=True` and inlined CSS
- Passes to `html_to_pdf_bytes()` from `scaffold.core.pdf_export`
- Filename: `threat_model_{id}_{slug}.pdf`

### 7.2 HTML (`export_html`)
- Same template, returns as a downloadable `.html` file with embedded CSS
- Useful for sharing or archiving without requiring the app

### 7.3 CSV (`export_csv`)
- Flat CSV with one row per `ThreatScenario`
- Columns: id, title, stride_category, asset, likelihood, impact_score, risk_score, risk_level, treatment, status, mitigation, owner

### 7.4 Export Report Layout (`export_report.html`)
1. Cover page: model title, scope, date, owner
2. Table of Contents
3. Executive summary: scenario counts by STRIDE-LM category, counts by risk level, counts by status
4. Risk matrix heat-map (HTML table rendered with Bootstrap color utilities)
5. One section per STRIDE-LM category with all scenarios in that category
6. Each scenario renders: title, asset, description, attack vector, CIA impact, likelihood/impact/score, treatment, mitigation
7. Appendix: asset list

---

## 8. Navigation

Add to `scaffold/apps/threat/__init__.py`:

```python
from scaffold.core.registry import NavEntry

NAVIGATION = [
    NavEntry(endpoint="threat.dashboard", label="app.navigation.threat", order=50),
]
```

Add translation keys:
- `en.json`: `"app": { "navigation": { "threat": "Threat Modeling" } }`
- `nl.json`: `"app": { "navigation": { "threat": "Dreigingsmodellering" } }`

---

## 9. Translations (new keys)

All new keys live under a top-level `"threat"` namespace in `en.json` / `nl.json`.

Key groups:
- `threat.dashboard.*` — list page labels
- `threat.model_form.*` — create/edit model form
- `threat.asset_form.*` — asset form
- `threat.scenario_form.*` — full scenario form, STRIDE-LM category labels
- `threat.scenario_detail.*` — detail view labels
- `threat.export.*` — export page headers
- `threat.flash.*` — flash messages (created, updated, deleted, archived)
- `threat.stride.*` — human-readable labels for each STRIDE-LM category
- `threat.risk_level.*` — low / medium / high / critical labels
- `threat.status.*` — identified / analysed / mitigated / accepted / closed

---

## 10. Database Migration

After implementing models, generate the migration:

```bash
poetry run flask --app scaffold:create_app db migrate -m "add threat modeling module"
poetry run flask --app scaffold:create_app db upgrade
```

Tables created: `threat_models`, `threat_model_assets`, `threat_scenarios`, `threat_scenario_controls`.

---

## 11. Tests

New test file: `tests/test_threat_routes.py`

Test cases:
1. `test_dashboard_requires_login` — anonymous → 302 to login
2. `test_create_threat_model` — POST valid form → 302, model exists in DB
3. `test_create_asset` — POST asset form → asset created
4. `test_create_scenario_stride_categories` — one test per STRIDE-LM category
5. `test_risk_score_computation` — unit test `compute_risk_score()` matrix
6. `test_export_csv` — authenticated GET → 200, content-type text/csv
7. `test_export_html` — authenticated GET → 200, content-type text/html
8. `test_archive_model` — POST archive → is_archived True
9. `test_delete_scenario` — POST delete → scenario removed
10. `test_model_detail_shows_scenarios` — GET detail → all scenario titles present

---

## 12. Implementation Order

| Step | Task |
|---|---|
| 1 | Create `scaffold/apps/threat/models.py` with all four models and enums |
| 2 | Generate & run Alembic migration |
| 3 | Create `scaffold/apps/threat/forms.py` |
| 4 | Create `scaffold/apps/threat/services.py` (risk scoring + CSV export helper) |
| 5 | Create `scaffold/apps/threat/routes.py` (all routes listed in §4) |
| 6 | Create `scaffold/apps/threat/__init__.py` (register + NAVIGATION) |
| 7 | Add translation keys to `en.json` and `nl.json` |
| 8 | Create Jinja2 templates (dashboard → model detail → scenario form → export) |
| 9 | Write tests in `tests/test_threat_routes.py` |
| 10 | Register module in `scaffold/config.py` `_DEFAULT_MODULES` |

---

## 13. Open Design Decisions

| Decision | Options | Recommendation |
|---|---|---|
| Link scenarios to Risk module? | Yes (FK to `risk_items`) / No (standalone) | Start standalone; FK can be added later |
| Link scenarios to CSA controls? | Yes (M2M `threat_scenario_controls`) / No | Include — adds immediate value for mitigations |
| Link assets to BIA Components? | Yes (FK to `bia_components`) / No | Include as optional FK field on `ThreatModelAsset` |
| Risk matrix: stored vs computed | Store `risk_score`/`risk_level` in DB | Store — easier to filter/sort/export |
| Multi-user collaboration | Single owner per model / shared | Single owner with viewer list — defer until needed |
| STRIDE-LM vs STRIDE | Include Lateral Movement | Yes — key for modern threat assessment |
