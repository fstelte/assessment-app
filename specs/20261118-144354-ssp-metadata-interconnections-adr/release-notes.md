# Release notes: SSP usability pass and risk owner from threat

## What's new

- **SSP metadata saves again.** Saving **Edit SSP** silently did nothing,
  because the form expected three C/I/A override fields that the page never
  showed. They are gone; C/I/A stays derived from the BIA.
- **Interconnections follow the BIA.** The systems listed under the BIA's
  *Interfaces* are added to the SSP's interconnections automatically, on
  every view, edit and export, not only when the SSP is created. You keep
  recording the agreement, direction, contact and notes in the SSP.
  - BIA rows show a **BIA** badge; their name can only be changed in the
    BIA.
  - Rows whose system was removed from the BIA show **No longer in BIA** and
    can then be deleted. Rows still in the BIA cannot be deleted.
  - A manual row with the same name as a new BIA interface is taken over, not
    duplicated.
- **Laws/regulations/policies and monitoring frequency are picked from
  lists.** Administrators maintain both under **Administration → SSP lists**
  (`/admin/ssp-options`). Laws are a multi-select; the monitoring frequency is
  a single choice.
- **Continuous monitoring is explained** as monitoring the progress on the
  SSP.
- **Architecture overview accepts PDFs and can be removed.** PNG, JPEG or PDF
  up to 10 MB, with the rules shown under the upload field and a specific
  message when a file is refused. PDFs show as a card with **Download PDF**.
  Each version can be deleted.
- **POA&M is Jira-first.** Its purpose is explained: steering and monitoring
  improvements to the system in the plan. Items need only a weakness, a
  status and a **Jira link**. Contact, date, resources, cost and milestones
  are optional and collapsed.
- **Security ADRs.** The ADR section is renamed and explains that only
  security-relevant decisions belong there. You can link to an **ADR register**
  page for the whole SSP, link each ADR to its external description (Context
  and Decision become optional), and **delete** ADRs.
- **Risk owner comes from the threat.** A risk synced from a threat scenario
  gets the scenario's owner, or the threat model's owner when the scenario has
  none. PASTA risks get the threat model's owner.

## Who can do what

- SSP pages keep their access: any signed-in user can edit, and therefore
  also delete architecture overview versions, ADRs and interconnections that
  are no longer in the BIA. Each delete asks for confirmation and is
  audit-logged with the user. The residual risk is a mistaken or deliberate
  delete by a signed-in user; the audit trail shows who did it.
- **SSP lists** are admin-only and require a recent sign-in, like the other
  admin catalogues.

## Behaviour changes to be aware of

1. **The free-text "Laws, Regulations & Policies" field is gone.** Its text
   stays in the database but is no longer shown, edited or exported.
   Administrators should create the list options and editors should re-select
   them per SSP.
2. **Existing free-text monitoring frequencies became list options.** Values
   that differ only in case or spaces ("Monthly", " monthly") became one
   option. Check the list after the upgrade and tidy names if needed.
3. **Opening an SSP can add interconnection rows** (from the BIA). This is
   recorded as `ssp_interconnections_reconciled` in the audit log.
4. **PDF overviews download instead of opening in the browser.**
5. **Threat sync now overwrites the risk owner** of threat-linked risks, and
   clears it when the scenario and threat model have no owner. A changed
   owner resets an existing owner approval, as any owner change does. Set the
   owner on the scenario or threat model.

## Upgrade

1. Run `flask db upgrade`. Revision `20261118_0003` creates `ssp_options` and
   `ssp_plan_laws` and adds `ssp_plans.monitoring_frequency_id` and
   `ssp_plans.adr_register_url`, which replace `ssp_plans.monitoring_frequency`.
   It also adds `ssp_interconnections.source`, `ssp_poam_items.jira_url`,
   `adr_records.external_url` and `adr_records.status_before_supersede`, and
   makes `adr_records.context`/`decision` nullable. Tested
   upgrade → downgrade → upgrade on PostgreSQL 18.
2. **Redeploy the gateway container.** `docker/nginx/nginx.conf` now sets
   `client_max_body_size 12m;`. Without it, nginx rejects uploads over 1 MB
   with a bare 413; this was the likely cause of "the architecture overview
   does not always upload". If you run your own gateway or a load balancer in
   front of it, raise its body-size limit to at least 12 MB too (see
   `docs/deployment.md`).
3. No new environment variables. The new translation keys are in both
   `en.json` and `nl.json`.

Downgrading `20261118_0003` restores the free-text frequency from the option
name, fills empty ADR context/decision with an empty string and drops the
option lists, Jira links, ADR links and the interconnection source.

## Known limitations and follow-ups

- No Jira integration: the link is not checked and Jira status is not shown.
- External links (ADR register, ADR link, Jira link) are not checked for
  dead links.
- PDF overviews are not previewed and are not part of the SSP export (the
  export did not include the overview before either).
- List option names are not translated per language.
- Renaming an interface in the BIA leaves the old row marked "No longer in
  BIA"; details have to be moved by hand.
- **Found during this work, not fixed:** `GET /admin/risks/<id>` (admin risk
  edit) returns 500, because `admin/_risk_form.html` renders fields that
  `RiskForm` does not have (`category`, `owner_id`, `probability`, `status`).
  The admin risk page therefore does not show the new owner hint. The main
  risk edit page (`/risk/<id>/edit`) does.
- A fresh SQLite database cannot run the whole migration chain (an older
  revision alters a constraint without batch mode). PostgreSQL, the
  production database, is unaffected.
