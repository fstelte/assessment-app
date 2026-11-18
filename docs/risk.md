# Risk Assessment Workspace

The risk module provides a single workspace for tracking identified risks across Business Impact Analysis (BIA) components, linking CSA controls, and tuning the severity matrix that feeds dashboards and exports.

## Access & Roles

- Any signed-in user can open the risk workspace (`/risk`), the Risk overview (`/risk/overview`), `/risk/new` and `/risk/<id>/edit`. The **Sync from threats** button is only shown to the `admin` and `assessment_manager` roles; the endpoint itself only requires a signed-in user.
- The API under `/api/risks` requires a fresh login and the `admin` role.
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
7. Optionally assign a treatment owner, due date, and supporting plan text before saving. The owner is also the person who approves the risk (see below).

## Workspace and Overview

- **The risk workspace (`/risk`) lists open risks only.** A risk leaves it as soon as it is closed: by hand with **Close & archive**, or by the threat sync when its scenario is Accepted or Closed or isn't treated by Mitigate. The cards, summary figures, matrix and approval counts only cover open risks. When every risk is closed, the workspace shows "No open risks." with a link to the closed risks on the overview.
- **Cards are collapsed** to one line by default: severity, title, actual score, approval state, due status and the **Mitigated** marker. Click a card to open it, or use **Expand all** and **Collapse all**. A link to `/risk/#risk-<id>` opens that card.
- **The Risk overview (`/risk/overview`)** lists every risk, open and closed, in a table. The columns are severity, title (with a **Threat** or **PASTA** label), actual score, treatment, owner, approval state, BIA and status. Open risks come first, then by highest actual score, then by title. A closed and mitigated risk shows "Closed on D".

| Filter | Values |
|---|---|
| `status` | `all` (default), `open`, `closed`; any other value means `all` |
| `bia` | A BIA id, repeatable (`?bia=3&bia=7`); unknown ids are ignored |

### Reopening a Closed Risk

Open the risk from the overview. Its edit page shows a **This risk is closed** banner with the closing date.

- **Manual and PASTA risks:** click **Reopen risk**. Republishing a PASTA conclusion also reopens its risk.
- **Threat-linked risks:** there is no button. They reopen when their threat scenario no longer closes them, because opening the edit page re-syncs the risk from its scenario. If the scenario has been reopened already, the page opens with the risk open.

## Owner Approval

The risk's owner (the **Owner** field, `treatment_owner_id`) signs off on the risk's assessment and treatment.

- **What is approved:** chance, impact and treatment, plus the residual chance, residual impact and **Mitigated** marker when they are set.
- **Who can decide:** only the owner, from the **Owner approval** panel at the top of `/risk/<id>/edit`. Admins and managers cannot decide on the owner's behalf; they can reassign the owner instead. A risk without an owner shows **No owner** and cannot be approved.
- **Approve or reject:** a comment is optional when approving and required when rejecting (max. 2000 characters). The owner can change a decision at any time; each decision is recorded separately.
- **Reset:** changing the chance, impact, treatment, residual values, Mitigated marker or owner puts the risk back to **Awaiting approval**, whether the change comes from the risk form, the admin register, the API, the threat-scenario sync or a PASTA publish. Edits to the title, description, tickets, components, controls, impact areas, due date or treatment plan, and closing or reopening the risk, keep the decision.
- **After a reset** the panel shows the last rejection ("Previously rejected by … on …") so whoever revises the risk can see why. This reason comes from the audit log.
- **Changed while open:** if a material field changes while the owner has the page open, the decision is refused with "This risk changed since you opened it" and the owner reviews it again.

### Finding Risks to Decide

The dashboard's **Approval** filter lists open risks only and combines with the BIA filter (for example `/risk/?approval=mine&bia=3`):

| Filter | Shows |
|---|---|
| `mine` – Awaiting my approval (n) | Risks you own with no decision or a rejection |
| `awaiting` – Awaiting approval | Risks that have an owner but no decision |
| `rejected` – Rejected | Rejected risks |

Every card shows its approval state: **Awaiting approval**, **Approved**, **Rejected** or **No owner**.

### Audit Events

| Event | When |
|---|---|
| `risk_approved` / `risk_rejected` | The owner decides; includes the comment and the approved chance, impact, treatment, residual values and actual score |
| `risk.updated` | Generic field audit; a reset shows `approval_*` fields changing to empty |
| `risk_synced_from_threat` | Threat sync; `approval_reset: true` when the sync voided a decision |

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
- Approval fields are read-only: responses include `approval_status`, `approval_state` (`no_owner`, `awaiting`, `approved`, `rejected`), `approval_decided_at`, `approval_decided_by` and `approval_comment`. `POST` and `PUT` ignore them; there is no API to approve or reject.
- A `PUT` without `treatment_owner_id` clears the owner, which also resets the approval. Always send the owner when updating a risk.

## Troubleshooting

- **No components in the selector** – ensure at least one BIA context scope has a risk flag enabled and contains components.
- **CSA control required errors** – select at least one control whenever the treatment is `mitigate`. The error string is `Select at least one CSA control when the treatment strategy is Mitigate.`
- **Overlapping severity ranges** – update the surrounding ranges so `max_score` for one severity is strictly less than the `min_score` of the next severity.
- **403 errors on `/risk`** – the workspace only requires a signed-in user; check that the session hasn't expired. The `/api/risks` endpoints also require the `admin` role and a fresh login.
- **A risk disappeared from the workspace** – it was closed, by hand or by the threat sync. Find it on the Risk overview (`/risk/overview?status=closed`) and reopen it from its edit page.
- **403 when approving or rejecting** – only the user set as the risk's owner can decide, and admins are not exempt. Assign the right owner first.
- **Approval went back to "Awaiting approval"** – a material field (chance, impact, treatment, residual values, Mitigated, owner) changed. The audit log shows which change and who made it; threat-linked risks can be reset by the scenario sync.

## PASTA Risk Publication

Risk items can be created automatically from a completed PASTA threat model analysis (stage 7). The publication workflow treats the PASTA model as the source of truth.

### Publication Gates

A stage-seven `PastaRiskConclusion` must satisfy all of the following before publishing:

1. `likelihood_score` and `impact_score` are both set (1–5 scale).
2. `overall_score` has been derived (saved via the scoring form).
3. The parent `PastaFinding` has a non-empty `description` (serves as the risk narrative).
4. The finding status is not `needs_revalidation`.
5. The parent `PastaStageRecord` (stage 7) is not in `needs_revalidation` state.

### Publication Flow

1. Open the PASTA model detail page.
2. In stage 7, locate a `risk_conclusion` finding and click **Add Scores** (or **Edit Scores**).
3. Set likelihood and impact (1–5), choose a treatment strategy, and optionally add publication notes.
4. Save — the overall score is derived from the likelihood × impact matrix (`compute_pasta_overall_score`).
5. If all gates pass, click **Publish to Risk Workspace** — this calls `publish_pasta_conclusion_to_risk`.
6. The linked risk workspace entry is created (or refreshed on republish). The `published_risk_id` FK on the conclusion points to it.
7. Republishing after a source update refreshes the existing Risk row rather than creating a duplicate.

### Dashboard Integration

Risk items that originate from a PASTA model display a **PASTA source** badge on the risk dashboard with a direct link back to the originating `PastaRiskConclusion` scoring form.

### Publication State Values

| State | Meaning |
|---|---|
| `not_published` | Conclusion exists but has not been published to the risk workspace. |
| `published` | Conclusion has been successfully published; `published_risk_id` is set. |
| `needs_revalidation` | An upstream PASTA stage was updated after publication; the conclusion must be reviewed and republished. |
