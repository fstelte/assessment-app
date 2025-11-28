# UI Style Guide

The scaffold application standardises on Bootstrap 5 with a dark-mode first design.

## Layout

- Base template defines a responsive dark header with dynamic navigation, optional breadcrumb slot, and content area.
- Dark mode is the default; provide a toggle to switch to light mode and store preference in user profile.
- Use responsive utilities to ensure usability on tablets.
- The navigation component hides the hamburger toggle on `lg` and wider breakpoints (`.d-lg-none`) so the button only appears when the collapse panel is initially hidden on narrow viewports.
- The BIA detail/context view builds on a flex layout (`d-flex flex-column flex-lg-row`) so the components table can grow while the Risk/Overview/Summary stack stays adjacent (`flex-grow-1` for the table, `flex-shrink-0 w-100 w-lg-auto` with min/max constraints for the sidebar) even as the viewport changes.
- CSA dashboard cards (assessments, controls, workflow) and quick-action buttons use `row row-cols-*` patterns to keep each set aligned in a single row on medium-plus breakpoints; avoiding explicit column numbers prevents single buttons from wrapping below the others when additional actions appear.

## Components

- Alerts: use Bootstrap contextual colors; reserve `danger` for blocking errors, `warning` for MFA prompts.
- Tables: prefer `table-dark` with striping for readability.
- Forms: apply floating labels where possible; display validation errors inline.
- Form tooltips: use the `render_field_with_tooltip` macro (or the `tooltip-wrapper` utility classes) to expose help text without JavaScript, including a visually hidden description linked via `aria-describedby`.
- Buttons: primary actions use `btn-primary`, secondary navigation uses `btn-outline-light`; admin shortcuts can use `btn-outline-warning` for emphasis.

## Icons & Visuals

- Use Bootstrap Icons or Heroicons (ensure license compliance).
- Keep charts accessible; provide textual summaries for screen readers.

## Accessibility

- Maintain contrast ratios WCAG AA or better.
- Ensure forms include ARIA descriptions for MFA inputs and token fields.
- Provide skip navigation link at the top of the page.

## Future Work

- Consolidate existing BIA and CSA templates into shared components (`scaffold/templates/partials/`).
- Document pattern library once components are refactored.
