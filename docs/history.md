# Change History

This log tracks major decisions and milestones as the scaffold application evolves.

| Date | Change | Notes |
| --- | --- | --- |
| 2025-11-28 | UI export parity and layout polish | Navbar collapse toggler now hides on large screens, BIA detail/context cards use a flex row so the Risk/Overview/Summary stack stays adjacent while exports inline `app.css` for identical styling, and CSA dashboard cards/buttons share the same responsive row to avoid wrapping. |
| 2025-11-23 | CSA assessment deletion controls | Admins and assessment managers can now remove assessments (with cascaded responses/assignments) from the detail view, plus new translations and tests. |
| 2025-11-23 | Optional Certbot & security overlays | Added automated Let's Encrypt support plus fail2ban and CrowdSec sidecars for standalone deployments, with new `.env.production` toggles and compose overlays. |
| 2025-11-16 | DPIA workflow overhaul | Added colored status badges (in progress, in review, finished, abandoned), CRUD controls for risks/measures, and severity badge alignment with BIA colors. |
| 2025-11-15 | CSS-only form tooltips and translations | Added reusable tooltip macro, styling, and localisation updates for BIA forms with accessible hover/focus helpers. |
| 2025-11-05 | BIA owner assignment and AI risk display updates | Owner reassignment no longer changes last-update timestamps, risk indicators show yes/no, and AI risk tables now include motivation, colour-coded badges, and translations. |
| 2025-11-04 | CSA Question translatoon, work on some of the badges | |
| 2025-10-30 | Translated all parts of the application, add docker support. | |
| 2025-10-31 | Backup service and operational tooling added | Added a dedicated backup container, compression, retention (2 days), optional S3 upload, status endpoint and healthcheck for automated backups. |
| 2025-10-29 | Localization enhancements | Added per-user locale preference, login selector, and rebuilt translation catalogs. |
| 2025-10-24 | Scaffold repository initialised | Created Poetry project, registry skeleton, documentation placeholders. |
| 2025-10-24 | BIA/CSA models scaffolded | Namespaced models registered under unified metadata. |
| 2025-10-24 | Session security & auth scaffolded | Combined auth blueprint, MFA utilities, and middleware. |
| 2025-10-24 | Alembic environment added | Unified migrations harness prepared for future revisions. |
| 2025-10-24 | BIA detail view migrated | Added CIA impact summary, component table, and AI indicators. |
| 2025-10-24 | Unified model registry noted | Documented migration/back-compat requirements for merged schema. |
| 2025-10-24 | Auth flow consolidated | Centralised MFA/session helpers and reintroduced security headers. |
| 2025-10-24 | Admin module scaffolded | Ported MFA management to shared helpers and added admin blueprint. |
| 2025-10-24 | Navigation refactored | Introduced dynamic Bootstrap dark-mode nav with registry-driven entries. |
| 2025-02-08 | BIA environment exports and audit hardening | Component environments appear in CSV/SQL exports, HTML export reuses the context detail template with print styles, audit event JSON parsing is more tolerant, and translations refreshed. |
| TBD | BIA models migrated | Pending reconciliation of models and migrations. |
| TBD | CSA models migrated | Pending integration work. |
| TBD | Unified auth released | Merge MFA flows, role mapping, and session security. |
| TBD | Bootstrap dark theme complete | Template consolidation and design review. |
| TBD | Database guides published | Hands-on docs for PostgreSQL deployments. |
