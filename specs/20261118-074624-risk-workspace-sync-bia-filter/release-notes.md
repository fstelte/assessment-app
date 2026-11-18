# Release notes: open-only risk workspace, risk overview and collapsible cards

## What's new

- **The risk workspace shows open risks only.** Any risk that is closed no
  longer appears on `/risk/`. This includes risks closed by hand and
  threat-linked risks closed by the scenario sync, because their scenario is
  Accepted or Closed or isn't treated by Mitigate. Closed risks are also left
  out of the summary figures, the matrix and the "Awaiting my approval"
  count. The BIA and approval filters work as before, on the open risks.
- **New Risk overview page (`/risk/overview`).** A compact table of every
  risk, open and closed, linked from the workspace header.
  - Columns: severity, title (linking to the edit page, with a "Threat" or
    "PASTA" label), actual score, treatment, owner, approval state, BIA and
    status (Open, Mitigated or "Closed on D").
  - Filter by status (All, Open or Closed) and by BIA, for example
    `/risk/overview?status=closed&bia=3`.
  - Open risks come first, then by highest actual score, then by title.
- **Collapsible risk cards.** Workspace cards start collapsed to one line:
  severity, title, actual score, approval state, due status and the
  Mitigated marker. Click a card to open it. "Expand all" and "Collapse all"
  open or close every card. A link to `/risk/#risk-<id>` opens that card.
- **Reopen from the edit page.** A closed risk's edit page shows a "This risk
  is closed" banner with the closing date.
  - Manual and PASTA risks have a **Reopen risk** button there.
  - Threat-linked risks show "Reopens when its threat scenario is reopened."
    instead. Opening the page re-syncs the risk from its scenario, so it
    reopens on its own once the scenario no longer closes it.
- **Clearer messages.** Closing a risk now says 'Risk "…" closed. You can
  find it on the Risk overview.' A workspace where every risk is closed shows
  "No open risks." with a link to the closed risks on the overview.

## Who can do what

- The overview has the same access as the workspace: any signed-in user.
- Reopening uses the existing reopen action, with no new permissions.

## Behaviour changes to be aware of

1. **Closed and archived risks no longer appear on the risk workspace**,
   its summary figures or its matrix. Find them on the **Risk overview**.
   Before, an unfiltered workspace showed them with a Reopen button.
2. **The workspace cards have no Reopen button any more.** Reopen a closed
   risk from its edit page, which you reach from the overview.
3. **Cards are collapsed by default**, and the page doesn't remember which
   cards were open.

## Upgrade

- No database migration and no new configuration.
- The new translation keys are in both `en.json` and `nl.json`.

## Known limitations and follow-ups

- The overview has no column sorting, per-row actions or pagination. It
  loads every risk that matches the filters.
- The overview has no approval filter. Use the workspace's Approval filter,
  which lists open risks.
- Which scenario statuses close a risk is unchanged: Accepted still closes
  it.

---

# Release notes: risk owner approval

## What's new

- **Risk owners approve the risks they own.** The risk's owner (the "Owner"
  field on the risk) can approve or reject a risk on its edit page. The
  decision covers the risk's chance, impact and treatment, and the residual
  values and Mitigated marker when they are set. Rejecting needs a comment.
  The page shows who decided, when, and the comment.
- **The owner can change their mind.** An approved risk can be rejected and
  the other way round, and approving again records a new decision. Every
  decision is logged.
- **A material change resets the approval.** If the chance, impact,
  treatment, residual values, Mitigated marker or owner changes, the risk
  goes back to "Awaiting approval". This applies whether the change comes
  from the risk form, the admin risk register, the API, the threat-scenario
  sync or a PASTA publish. Changes to the title, description, tickets,
  components, controls, impact areas, due date or treatment plan don't reset
  it. Closing or reopening a risk doesn't either.
- **The last rejection reason stays visible.** After a reset, the edit page
  shows "Previously rejected by X on D" with the comment, so whoever revises
  the risk can see why it was rejected.
- **Find the risks that need a decision.** The risk dashboard has an
  "Approval" filter:
  - **Awaiting my approval (n):** your open risks with no decision or a
    rejection.
  - **Awaiting approval:** every open risk that has an owner but no decision.
  - **Rejected:** every open rejected risk.

  It works together with the BIA filter (`/risk/?approval=mine&bia=3`). The
  cards, summary figures and matrix follow it. Every card shows its approval
  state: Awaiting approval, Approved, Rejected or No owner.
- **Audit trail.** Decisions are logged as `risk_approved` and
  `risk_rejected`, with the comment and the values that were approved. The
  generic risk audit records approval resets. A reset caused by the threat
  sync is also flagged as `approval_reset: true` on its
  `risk_synced_from_threat` event.
- **API.** `GET /api/risks` adds read-only `approval_status`,
  `approval_state`, `approval_decided_at`, `approval_decided_by` and
  `approval_comment`. The API can't approve or reject: `POST` and `PUT`
  ignore these fields.

## Who can do what

- **Approve or reject:** only the user set as the risk's owner. Admins and
  risk managers can't decide for the owner. They can reassign the owner, and
  that resets the approval.
- **A risk without an owner** can't be approved. It shows "No owner" until
  someone assigns one.
- **Owners may approve a risk they edited themselves.** The audit trail shows
  both the edit and the approval.
- **See approval states and use the filters:** any signed-in user, the same
  as the rest of the risk dashboard.

## Behaviour changes to be aware of

1. **Every existing risk starts as "Awaiting approval"**, or "No owner" if it
   has no owner. Nothing is approved automatically, so owners will see their
   whole backlog under "Awaiting my approval".
2. **The threat sync can reset approvals.** When a linked scenario's
   likelihood, impact, treatment, residual values or status (mitigated or
   not) changes, its risk goes back to "Awaiting approval" on the next sync,
   including when someone opens the risk.
3. **An API `PUT` without `treatment_owner_id` clears the owner**, as it
   already did. That now also resets the approval. API clients that update
   risks should always send the owner.
4. **A decision is refused if the risk changed in the meantime.** If someone
   edits a material field while the owner has the page open, Approve or
   Reject shows "This risk changed since you opened it". The owner has to
   review it again, and the comment they typed isn't saved.

## Upgrade

- Migration `20261118_0002` adds four nullable columns to `risk_items`:
  `approval_status`, `approval_decided_at`, `approval_decided_by_id` (a
  foreign key to `users`, set to NULL when the user is deleted) and
  `approval_comment`. It needs no backfill and runs with the usual
  `flask db upgrade` during deployment.
- **Downgrade** drops the four columns, and all approval decisions are lost.
  The `risk_approved` and `risk_rejected` audit entries remain.
- Tested: upgrade, then downgrade, then upgrade again, on PostgreSQL 16.
- No new configuration or environment variables.

## Known limitations and follow-ups

- No notifications. Owners have to use the "Awaiting my approval" filter.
- The admin risk register doesn't show the approval state.
- Bulk database updates (`query.update()`) bypass the reset. No code path
  uses them on the approval-relevant fields today.
- If the decider's account is deleted, the current decision shows "Unknown
  user". An earlier rejection still shows the name stored in the audit log.
- The "Previously rejected" reason comes from the audit log, so it isn't
  shown when audit logging is turned off.

---

# Release notes: risk workspace targeted sync, BIA filter and actual risk score

Released in 2026.11.5.

## What's new

- **Synced risks link only the affected components.** A risk created from a
  threat scenario now links just the BIA components that the scenario lists as
  threatened assets. The match is by name, ignoring case and surrounding
  spaces. Before, a scenario with no match linked every component in the BIA.
- **Filter the risk workspace by BIA.** You can select one or more BIAs. The
  risk cards, the summary figures and the matrix then only show risks with a
  component in those BIAs. The filter is part of the URL
  (`/risk/?bia=3&bia=7`), so you can bookmark or share it.
- **The actual risk is shown.** Every risk can now record a residual impact,
  a residual chance and a "Mitigated" marker. When a risk is mitigated and has
  both residual values, the residual score is used everywhere. Otherwise the
  initial score is used. This applies to:
  - the risk cards (with an "Initial: X → Residual: Y" hint);
  - the risk matrix;
  - the "High & critical" count;
  - the risk edit page;
  - the admin risk register;
  - the SSP risk summary (on screen and in the PDF export).
- **Threat-linked risks follow their scenario.**
  - A scenario with status **Mitigated** now keeps its risk open, with the
    residual score. Before, it closed the risk.
  - **Accepted** and **Closed** still close the risk. So does a scenario
    whose treatment isn't Mitigate.
  - On the risk form, the fields the scenario controls are read-only and link
    to the scenario: title, description, impact, chance, treatment, residual
    values, Mitigated, components and controls.
- **Audit trail.** Changes made by the sync are logged as
  `risk_synced_from_threat`, listing only the fields that changed, and new
  risks as `risk_created_from_threat`. Manual create and update events now
  include the mitigated marker and the residual values.
- **API.** `GET /api/risks` adds `mitigated_at`, `residual_impact`,
  `residual_chance`, `residual_score`, `actual_score` and `actual_severity`.
  `score` and `severity` still mean the initial score. `POST` and `PUT` accept
  `residual_impact`, `residual_chance` and `mitigated`. A field you leave out
  stays unchanged, and `null` clears it.

## Behaviour changes to be aware of

1. **Synced risks lose components on their next sync.** Risks that got every
   component in the BIA through the old fallback keep only the components that
   match the scenario's threatened assets. If nothing matches, they keep none.
   The change is visible in the audit log.
2. **Archived risks of mitigated scenarios reopen.** Before, mitigated
   scenarios archived their risk. On the next sync (saving the scenario,
   "Sync from threats", or opening the risk) such risks reopen as mitigated.
3. **Opening a threat-linked risk syncs it.** The edit page refreshes the risk
   from its scenario. If the scenario is Accepted or Closed, that closes the
   risk.
4. **The "Mitigation tracks" figure is now called "Treatment: mitigate".** It
   still counts risks whose treatment is mitigate.

## Fixes

- An API `PUT` that kept one of the risk's existing impact areas failed with
  a 500 error (unique constraint `uq_risk_impact_area`).

## Upgrade

- Migration `20261118_0001` adds three nullable columns to `risk_items`:
  `mitigated_at`, `residual_impact` and `residual_chance`. Existing rows need
  no backfill. Their actual score equals their initial score until they are
  synced or edited. It runs with the usual `flask db upgrade` during
  deployment.
- **Downgrade** drops the three columns, and the mitigated and residual data
  is lost.
- Tested: upgrade, then downgrade, then upgrade again, on PostgreSQL 16.

## Known limitations and follow-ups

- The API can still change fields of a threat-linked risk that the scenario
  owns. The next sync overwrites them.
- The SSP risk summary counts a risk once for each component it has in that
  BIA, so one risk can be counted twice. This was already the case.
- PASTA-published risks have no residual values from PASTA. You can set them
  by hand on the risk form.
