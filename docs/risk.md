# Risk Assessment Workspace

The risk module provides a single workspace for tracking identified risks across Business Impact Analysis (BIA) components, linking CSA controls, and tuning the severity matrix that feeds dashboards and exports.

## Access & Roles

- Only users with the `admin` or `manager` roles can open `/risk`, `/risk/new`, and `/risk/<id>/edit`. The API under `/api/risks` requires a fresh login and the same roles.
- The admin-only `/admin/risk-thresholds` endpoint lets privileged users tune the severity matrix.

## Prerequisites

1. **Eligible BIA components** – a component must belong to a context scope where at least one of the `risk_assessment_*` flags is enabled. These components populate the multi-select on the risk form.
2. **CSA control catalogue** – mitigation workflows rely on CSA control metadata (`domain`, `section`, `description`) so the catalogue should be imported or created before launching the risk workspace.
3. **Severity thresholds** – populate `risk_severity_thresholds` with non-overlapping ranges (for example Low 1–5, Moderate 6–10, High 11–15, Critical 16–25). The UI exposes helpers to adjust the ranges later.

## Capturing a Risk

1. Navigate to `/risk` and select **New risk**.
2. Provide a short title and detailed description. The form enforces a 255-character limit for titles and requires descriptions to capture the scenario and trigger.
3. Select the impact and chance weights. The impact dropdown mirrors the BIA consequence scale (`Insignificant`, `Minor`, `Moderate`, `Major`, `Catastrophic`) and the score remains `impact_weight * chance_weight`; severity is resolved using the configured thresholds.
4. Choose one or more impact areas (`Operational`, `Financial`, `Regulatory`, `Human & Safety`, `Privacy`). These drive the chips rendered on the dashboard and provide context for downstream reporting.
5. Link every affected component. Only risk-enabled BIA components are listed. If no options appear, update the BIA context to enable one of the risk flags.
6. Choose a treatment strategy. When selecting **Mitigate**, the form and API both require at least one CSA control reference. Accept/Avoid/Transfer strategies can omit the control.
7. Optionally assign a treatment owner, due date, and supporting plan text before saving.

## Selecting CSA Controls for Mitigation

- Use the CSA domain identifier to match the control to the risk scenario. The dropdown is ordered by domain to make ISO/IEC 27002 references easy to spot.
- Always confirm that the control description aligns with the treatment plan. The system stores `domain`, `section`, and `description` so reviewers can validate the linkage from the risk dashboard.
- If the appropriate control does not exist, coordinate with CSA administrators to create it before finalising the risk entry. Mitigation submissions without a linked control are blocked by both the UI and API.
- Consider documenting how the control mitigates the risk directly within the treatment plan text—this helps auditors trace the reasoning without leaving the workspace.

## Configuring Severity Thresholds

1. Open `/admin/risk-thresholds` (admin role required).
2. Each severity renders its own form with `Min score` and `Max score` inputs. Enter new bounds and click **Save range** for the specific severity you are updating.
3. Overlapping ranges are rejected with `Thresholds cannot overlap` errors to maintain a clean severity matrix. Adjust adjacent ranges until every `min_score` is greater than the previous `max_score`.
4. Successful updates flash `Severity range for <severity> updated.`; the risk dashboard reflects the change immediately.

## API Usage

- `GET /api/risks` returns an array of serialized risks including derived `score`, `severity`, component snapshots, and CSA control metadata. Responses now expose a `controls` array plus a legacy `control` key for backwards compatibility.
- `POST /api/risks` and `PUT /api/risks/<id>` enforce the same validation rules as the UI, including the mandatory CSA control when `treatment` equals `mitigate`. Provide the list under `csa_control_ids`; the legacy `csa_control_id` field remains accepted for single-value clients.
- `DELETE /api/risks/<id>` removes the record and cascades component links/impact areas.

## Troubleshooting

- **No components in the selector** – ensure at least one BIA context scope has a risk flag enabled and contains components.
- **CSA control required errors** – select at least one control whenever the treatment is `mitigate`. The error string is `Select at least one CSA control when the treatment strategy is Mitigate.`
- **Overlapping severity ranges** – update the surrounding ranges so `max_score` for one severity is strictly less than the `min_score` of the next severity.
- **403 errors on `/risk`** – confirm the signed-in user has either the admin or assessment manager role.
