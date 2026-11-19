# Release notes: affected assets list with an "Add" overlay

## What's new

- **Selected components and assets are listed.** On the risk edit page
  (`/risk/<id>/edit`, **Related components**) and the threat scenario edit page
  (`/threat/<id>/scenarios/<id>/edit`, **Threatened assets**), the multi-select
  is replaced by a list of what is selected. Each row has a **×** button to
  remove it.
- **Add through an overlay.** **Add component** (risk) and **Add asset**
  (scenario) open an overlay. It lists the options that are not selected yet,
  with a search box that matches any part of the name, including the BIA
  name. Tick items and select **Add**. **Cancel**, Esc or a click outside
  the overlay discards the change. Nothing is saved until the form is saved.
- **Threat-linked risks show their components read-only.** There are no Add or
  × buttons. A note explains that the components come from the scenario's
  threatened assets and links to the scenario (**Open scenario**).
- The duplicate **Linked components** summary at the bottom of the risk edit
  page is removed. The list above it replaces it.

## Who can do what

Nothing changes. Any signed-in user can edit risks. Editing a scenario still
requires the `admin` or `assessment_manager` role. The **Open scenario** link
goes to the scenario detail page, which every signed-in user can open.

## Behaviour changes to be aware of

- **A scenario needs at least one threatened asset.** Saving the scenario edit
  page with none now shows "Select at least one threatened asset." and saves
  nothing. Before, an empty selection was ignored and the old assets silently
  stayed.
  - Exception: an old scenario that only has the legacy single asset (no
    threatened-assets list yet) still saves as before, and that asset is
    copied into the list.
  - Existing scenarios with no assets at all cannot be saved from the edit page
    until an asset is added.
- The **New risk** and **New scenario** pages keep the multi-select. The threat
  finding form is unchanged.

## Upgrade

- No database migration, settings or environment variables.
- `app.css` is rebuilt by the Docker image (`scaffold/tailwind_cli.py`), which
  picks up the new utility classes. Deploy as usual and rebuild the image.
- New translation keys: `asset_picker.*` and
  `threat.scenario_form.assets_required` (en, nl).

## Known limitations and follow-ups

- The picker needs JavaScript, like the app's other overlays.
- The shared `ui.js` modal helpers (`openModal`, `closeModal`) only toggle an
  unstyled `.show` class. The picker therefore opens its own overlay. Pages
  that rely on `data-modal-target` (for example the DPIA page) may not show
  their modals. This was not checked as part of this change.
- `tests/test_threat_routes.py` fails on main (19 of 21 tests) because of
  stale fixtures. Task 6 of this feature repairs it.
