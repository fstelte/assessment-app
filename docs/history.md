# Change History

This log tracks major decisions and milestones as the scaffold application evolves.

| Date | Change | Notes |
| --- | --- | --- |
| 2026-03-18 | Threat Modeling module (2026.3.12) | Added a new **Threat Modeling** module with full STRIDE-LM support. Introduces `ThreatModel`, `ThreatModelAsset`, and `ThreatScenario` models with risk scoring (likelihood × impact → level), treatment options (accept/mitigate/transfer/avoid), scenario lifecycle statuses, and M2M links to CSA controls and BIA components. Full CRUD routes, archive support, and CSV/HTML/PDF export of scenarios. Two Alembic migrations added; module registered as a default. BIA dashboard export sidebar refactored into collapsible dropdown menus. Translations expanded and tests added. |
| 2026-03-13 | BIA templates and utils cleanup | Polished `all_consequences`, `components`, and `requirements` templates; fixed a minor routing issue in BIA routes and corrected a utility function edge case. |
| 2026-03-10 | Audit trail fixes and translation refresh | Fixed the audit trail page layout and corrected missing/broken translation keys across the application (release 2026.3.10). |
| 2026-03-09 | BIA IT dependencies and consequence management (2026.3.9) | Improved UI for editing BIA components and managing consequences; fixed IT dependency handling and enhanced translations for better user experience. |
| 2026-03-09 | Information classification labels and MFA improvements (2026.3.8) | Overhauled information classification label display; strengthened MFA flow with usability and reliability improvements. |
| 2026-03-08 | Tools section added (2026.3.7) | New **Tools** section with five interactive utilities: AI Act Checker, CVSS Calculator, Risk Tool, Security Roadmap, and Cloud Sovereignty Framework. |
| 2026-03-07 | PDF export and CSS fixes (2026.3.6) | Added PDF export functionality for reports; fixed CSS inconsistencies in HTML/PDF exports. |
| 2026-03-07 | BIA dependencies overview fix (2026.3.5) | Corrected the dependencies overview display. |
| 2026-03-02 | Dashboard, filtering and translation fixes (2026.3.4) | Fixed multiple dashboard rendering issues, corrected filter behaviour, and updated translations. |
| 2026-03-01 | Dependency vulnerability fixes (2026.3.3) | Updated third-party dependencies to resolve known security vulnerabilities. |
| 2026-02-28 | Dashboard and visualisation updates (2026.3.2) | Fixed dashboard layout bugs and refreshed chart/visualisation components. |
| 2026-02-28 | BIA overview revamp and export button fix (2026.3.1) | Fixed broken export buttons on the BIA dashboard and context detail page; revamped the BIA overview page with richer information and a more user-friendly layout. |
| 2026-02-27 | Full Tailwind migration and consequence/maturity fixes (2026.2.12) | Removed Bootstrap entirely in favour of Tailwind CSS; fixed the availability and consequences form; corrected maturity assessment scoring logic; broadened consequence tables; updated translations. |
| 2026-02-25 | BIA archiving (2026.2.11) | Introduced BIA context archiving: new `bia_archive` migration, archive/unarchive routes, a dedicated archived-contexts view, and corresponding tests. Dashboard now shows archived count. |
| 2026-02-24 | Maturity scoring and bug fixes (2026.2.10) | Added scoring logic to the CMMI maturity assessment module; addressed miscellaneous bug fixes across the application. |
| 2026-02-24 | Author full-name fix for coordinator/responsible fields (2026.2.9) | Coordinator and responsible fields on BIA contexts now store the user's full name instead of their username. |
| 2026-02-18 | BIA context and component form overhaul (2026.2.8) | Significantly expanded BIA forms with improved validation and UX; revamped the context form template; updated the components list and edit-component views; refreshed English and Dutch translations. |
| 2026-02-15 | BIA component type/description fields and security hardening (2026.2.7) | Edit-component form now captures component type and description; tightened security headers; various CSS and JS quality improvements. |
| 2026-02-14 | BIA Tier classification | Added `BiaTier` model and management interface. BIA Contexts clearly display their criticality tier (Critical Infrastructure, Mission Critical, etc.), and admins can customize tier names via a new settings panel. |
| 2026-02-08 | BIA environment exports and audit hardening | Component environments appear in CSV/SQL exports, HTML export reuses the context detail template with print styles, audit event JSON parsing is more tolerant, and translations refreshed. |
| 2025-11-28 | UI export parity and layout polish | Navbar collapse toggler now hides on large screens, BIA detail/context cards use a flex row so the Risk/Overview/Summary stack stays adjacent while exports inline `app.css` for identical styling, and CSA dashboard cards/buttons share the same responsive row to avoid wrapping. |
| 2025-11-23 | CSA assessment deletion controls | Admins and assessment managers can now remove assessments (with cascaded responses/assignments) from the detail view, plus new translations and tests. |
| 2025-11-23 | Optional Certbot & security overlays | Added automated Let's Encrypt support plus fail2ban and CrowdSec sidecars for standalone deployments, with new `.env.production` toggles and compose overlays. |
| 2025-11-16 | DPIA workflow overhaul | Added colored status badges (in progress, in review, finished, abandoned), CRUD controls for risks/measures, and severity badge alignment with BIA colors. |
| 2025-11-15 | CSS-only form tooltips and translations | Added reusable tooltip macro, styling, and localisation updates for BIA forms with accessible hover/focus helpers. |
| 2025-11-05 | BIA owner assignment and AI risk display updates | Owner reassignment no longer changes last-update timestamps, risk indicators show yes/no, and AI risk tables now include motivation, colour-coded badges, and translations. |
| 2025-11-04 | CSA Question translatoon, work on some of the badges | |
| 2025-10-31 | Backup service and operational tooling added | Added a dedicated backup container, compression, retention (2 days), optional S3 upload, status endpoint and healthcheck for automated backups. |
| 2025-10-30 | Translated all parts of the application, add docker support. | |
| 2025-10-29 | Localization enhancements | Added per-user locale preference, login selector, and rebuilt translation catalogs. |
| 2025-10-24 | Navigation refactored | Introduced dynamic Bootstrap dark-mode nav with registry-driven entries. |
| 2025-10-24 | Admin module scaffolded | Ported MFA management to shared helpers and added admin blueprint. |
| 2025-10-24 | Auth flow consolidated | Centralised MFA/session helpers and reintroduced security headers. |
| 2025-10-24 | Unified model registry noted | Documented migration/back-compat requirements for merged schema. |
| 2025-10-24 | BIA detail view migrated | Added CIA impact summary, component table, and AI indicators. |
| 2025-10-24 | Alembic environment added | Unified migrations harness prepared for future revisions. |
| 2025-10-24 | Session security & auth scaffolded | Combined auth blueprint, MFA utilities, and middleware. |
| 2025-10-24 | BIA/CSA models scaffolded | Namespaced models registered under unified metadata. |
| 2025-10-24 | Scaffold repository initialised | Created Poetry project, registry skeleton, documentation placeholders. |
| TBD | BIA models migrated | Pending reconciliation of models and migrations. |
| TBD | CSA models migrated | Pending integration work. |
| TBD | Unified auth released | Merge MFA flows, role mapping, and session security. |
| TBD | Bootstrap dark theme complete | Template consolidation and design review. |
| TBD | Database guides published | Hands-on docs for PostgreSQL deployments. |
