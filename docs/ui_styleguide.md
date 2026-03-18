# UI Style Guide

The scaffold application uses **Tailwind CSS** (standalone CLI build) with a dark-mode-first design. Bootstrap was removed entirely in release 2026.2.12. The compiled output is `scaffold/static/css/app.css`, generated from source via `poetry run tailwind`.

## Theme System

- Dark mode is the default. The `<html>` element receives the `dark` class and a `data-theme="dark"` attribute, both driven by the user's `theme_preference` profile setting.
- CSS custom properties under `[data-theme]` selectors expose surface colours (`--color-surface`, `--color-surface-hover`, `--color-border`, `--color-text`, `--color-muted`) so components remain theme-neutral.
- Supply the `data-theme` toggle attribute on the `<body>` or a parent element to override locally where needed.

## Layout

- The base template (`scaffold/templates/base.html`) renders a full-height flex column: `flex flex-col min-h-screen`.
- Page content areas use `container mx-auto max-w-5xl px-4 sm:px-6` by default; override via the `main_container_class` block for wide dashboards.
- Navigation components hide the mobile-menu button at large breakpoints using standard Tailwind responsive prefixes (`lg:hidden`).
- Detail views use `flex flex-col lg:flex-row` to keep a growing main table alongside a pinned sidebar across viewport widths.
- Dashboard widget rows use `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` (or `auto-fit` patterns via inline `style` overrides) to avoid wrapping on mid-sized screens.

## Components

- **Alerts / flash messages**: use the CSS-variable-backed surface colours with a left coloured border. Critical errors use a red/`rose` border; warnings use amber; success uses green.
- **Tables**: no `table-dark` class — apply `w-full text-sm` and row hover via `hover:bg-[var(--color-surface-hover)]`. Wrap in a `overflow-x-auto` container for responsiveness.
- **Forms**: standard Tailwind form ring and focus styles; display validation errors with `text-red-500 text-xs mt-1` below the field.
- **Form tooltips**: use the `render_field_with_tooltip` macro which wraps the input with a `tooltip-wrapper` group and a visually-hidden description linked via `aria-describedby`.
- **Buttons**: primary actions use the `btn-primary` utility class defined in `app.css`; secondary navigation uses the outlined variant. Admin shortcuts can use amber tones for emphasis.
- **Dropdowns**: implemented as relative/absolute positioned Tailwind panels toggled with a small Alpine.js or vanilla JS `hidden` toggle — no Bootstrap JS dependency.
- **Cards**: `rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-sm` is the standard card shape.
- **Badges / status chips**: inline `px-2 py-0.5 rounded text-xs font-medium` with semantic colour fills (`bg-green-500/15 text-green-400` for success, etc.).

## Tailwind Build

```bash
# One-shot build
poetry run tailwind

# Watch mode during development
poetry run tailwind --watch
```

The `tailwind_cli.py` helper downloads the correct standalone Tailwind binary for the host platform and invokes it with `tailwind.config.cjs` and `scaffold/static/css/app.css` as the output target.

## Icons & Visuals

- Font Awesome (free, CDN) is loaded in the base template for common `fa-*` icons.
- Keep charts accessible; provide textual summaries alongside visual renderings.

## Accessibility

- Maintain contrast ratios WCAG AA or better (verify against the dark and light theme variants).
- Ensure forms include ARIA descriptions (`aria-describedby`) for MFA inputs and tooltip text.
- Provide a skip-to-content navigation link at the top of the page.

## Export Styling

- HTML/PDF exports inline `app.css` directly into the `<style>` tag using `export_css` so downloaded reports render offline without CDN assets.
- Navigation and action buttons are hidden during export via the `export_mode` template variable.

## Future Work

- Continue consolidating BIA, CSA, and threat module templates into shared partials under `scaffold/templates/partials/`.
- Document the full component catalogue once partials are extracted.
