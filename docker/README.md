# Docker Tooling

This directory centralises containerisation assets for the combined scaffold application.

## Images

- `Dockerfile` builds a production-ready image with Gunicorn.
- `entrypoint.sh` waits for the configured database, applies migrations, and starts the app.

Build locally:

```bash
docker build -t assessment-app -f docker/Dockerfile .
```

## Compose environments

Before using the compose files, copy `.env.example` or `env.production.example` to `.env` or `.env.production` (or define the variables manually) so Docker Compose picks up `COMPOSE_PROJECT_NAME=assessment_app`. Adjust the value if you need a different project prefix; the setting keeps container names predictable when running multiple stacks.

### Development (SQLite)

```bash
cp .env.example .env  # if you have not configured it yet
docker compose -f docker/compose.dev.yml up --build
```

The service exposes <http://localhost:5000> and uses the SQLite database defined in `.env`.

### Production (PostgreSQL)

```bash
cp docker/.env.production.example .env.production
# adjust secrets inside the file
docker compose -f docker/compose.prod.yml up --build -d
```

The entrypoint script waits for the database container, ensures the database exists, performs `flask db upgrade`, and then launches Gunicorn.

- PostgreSQL 18+ images changed their data directory layout. The compose files now mount the volume at `/var/lib/postgresql` and explicitly set `PGDATA=/var/lib/postgresql/data/pgdata`. If you are upgrading an existing named volume from PostgreSQL ≤17, move the contents of the volume into a `data/pgdata` subdirectory (for example with `docker run --rm -v postgres-data:/var/lib/postgresql alpine sh -c "set -eu; mkdir -p /var/lib/postgresql/data/pgdata; for entry in /var/lib/postgresql/*; do [ \"$entry\" = /var/lib/postgresql/data ] && continue; [ \"$entry\" = /var/lib/postgresql/data/pgdata ] && continue; mv \"$entry\" /var/lib/postgresql/data/pgdata/; done"`). This avoids `initdb` complaints about non-empty directories (e.g. `lost+found`).

- Maintenance mode: the `gateway` service (Nginx) proxies traffic to the Flask container and serves a generated maintenance page if the backend or database is unavailable. Adjust the template in `docker/templates/maintenance.html.tmpl` and control the contact details via `MAINTENANCE_CONTACT_EMAIL`, `MAINTENANCE_CONTACT_LABEL`, and `MAINTENANCE_CONTACT_LINK` in `.env.production`.

#### Gateway configuration choices

- **Behind an existing reverse proxy** – When a load balancer (NGINX, Traefik, CloudFront, etc.) already terminates TLS and forwards traffic internally, keep the bundled gateway simple. Only expose port `8000`, disable the Certbot overlay, and reference `docker/nginx/nginx.conf.example.behind-proxy.md` if you need a static configuration.
- **Public-facing gateway** – If the compose stack itself must terminate HTTP/HTTPS, enable the Certbot overlay (`docker/example.compose.certbot.yml`) and optional security profile (`docker/example.compose.security.yml`). Use `docker/nginx/nginx.conf.example.public.md` as a reference for the dynamic configuration that handles ACME challenges, HTTPS redirects, and CrowdSec snippets.

### Automated TLS (Certbot)

- Copy and adjust `.env.production` so `CERTBOT_ENABLED=true`, `CERTBOT_EMAIL`, `CERTBOT_PRIMARY_DOMAIN`, optional `CERTBOT_ADDITIONAL_DOMAINS` (comma-separated), and decide whether to keep `CERTBOT_FORCE_HTTPS=true` (redirects HTTP traffic to HTTPS once a certificate is present). Leave `CERTBOT_STAGING=true` while testing to avoid rate limits.
- Bring the stack up with the additional compose file: `docker compose --env-file .env.production -f docker/example.compose.prod.yml -f docker/example.compose.certbot.yml up -d gateway certbot`. The override publishes ports `80` and `443`, shares certificate volumes between Nginx and Certbot, and launches a lightweight loop that renews certificates based on `CERTBOT_RENEW_INTERVAL` (default 12 hours).
- Initial certificate issuance keeps the gateway on HTTP only; the `gateway` container reloads HTTPS automatically on restart. Trigger a reload after renewal with `docker compose exec gateway nginx -s reload` if you need the new certificate without redeploying.

### Perimeter Hardening (Fail2Ban & CrowdSec)

- Set `COMPOSE_PROFILES` in `.env.production` to include `fail2ban` and/or `crowdsec` (e.g. `COMPOSE_PROFILES=fail2ban,crowdsec`). The profiles gate the additional services defined in `docker/example.compose.security.yml` so you can keep disabled features out of your runtime.
- Fail2Ban watches the shared Nginx log volume and bans abusive source IPs via host firewall rules. Tune the detection window through `FAIL2BAN_MAXRETRY`, `FAIL2BAN_FINDTIME`, `FAIL2BAN_BANTIME`, and trusted ranges via `FAIL2BAN_IGNORE_IPS`. Bring it up alongside the main stack: `docker compose --env-file .env.production -f docker/example.compose.prod.yml -f docker/example.compose.security.yml up -d fail2ban`. The container requires `NET_ADMIN` and `NET_RAW`; ensure your deployment host allows these capabilities.
- CrowdSec analyses the same logs for behavioural signals and, with the optional firewall bouncer, shares block decisions across its community feed. Configure enrollment (`CROWDSEC_ENROLL_KEY`, `CROWDSEC_ENROLL_INSTANCE_ID`) and LAPI credentials (`CROWDSEC_LAPI_DEFAULT_PASSWORD`, `CROWDSEC_BOUNCER_API_KEY`). After the containers are up, create a bouncer key with `docker compose exec crowdsec cscli bouncers add nginx-firewall`, then paste the generated value into `.env.production` under `CROWDSEC_BOUNCER_API_KEY` and restart `crowdsec-firewall-bouncer`.
- The firewall bouncer runs with host networking and `NET_ADMIN` to manage iptables/ipset rules. Confirm your infrastructure permits these elevated privileges and that no upstream firewall (e.g. cloud security groups) blocks the relevant ports.

### Operational Helpers (Backup & Restore)

- `docker/compose.backup.yml` extends the production stack with:
  - `db-backup`: creates compressed snapshots on a schedule (`BACKUP_INTERVAL_SECONDS`) and optional S3 upload.
  - `db-restore`: watches a directory for new dump files, stops the configured application containers, restores the database, and brings the services back online.
- The backup helper is published as `ghcr.io/fstelte/assessment-app-backup` on pushes to `main`. Override `BACKUP_IMAGE` in your compose file (defaults to that tag) if you want to use a different registry or a locally-built image.
- Mount host directories so files persist outside the container lifecycle:
  - `./backups:/backups` (written by `db-backup`).
  - `./restore:/restore` (watched by `db-restore`; drop `.sql[.gz]`, `.dump[.gz]`, or `.db[.gz]` files into `/restore/incoming`).
- Control the automation with environment variables in `.env.production`:
  - `RESTORE_STOP_CONTAINERS` comma-separated list of container names to stop (for example `assessment_app-web-1`).
  - `RESTORE_START_CONTAINERS` optional list of extra containers to start after restoration (defaults to the ones that were stopped).
  - `RESTORE_WATCH_DIR`, `RESTORE_STATE_FILE`, `RESTORE_POLL_INTERVAL`, and `RESTORE_SQLITE_PATH` for fine-grained tuning.
- The restore container needs access to the Docker API to stop/start services: mount `/var/run/docker.sock` read-write into the container and ensure the names you provide exist (run `docker compose ps` to confirm).
- Start both helpers alongside the main stack once the environment variables are in place:

```bash
docker compose --env-file .env.production \
  -f docker/compose.prod.yml \
  -f docker/compose.backup.yml \
  up -d db-backup db-restore
```

- The `db-backup` image installs PostgreSQL client 18 from the upstream PGDG repository to stay compatible with server 18.x. Rebuild the image (`docker compose build db-backup`) after pulling updates so `pg_dump` matches your server version.
