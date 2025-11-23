#!/bin/sh
set -euo pipefail

log() {
  printf '[crowdsec] %s\n' "$*" >&2
}

ACQUIS_PATH="/etc/crowdsec/acquis.yaml"
mkdir -p "$(dirname "$ACQUIS_PATH")"

cat >"$ACQUIS_PATH" <<EOF
filenames:
  - ${CROWDSEC_NGINX_ACCESS_LOG:-/var/log/nginx/access.log}
labels:
  type: nginx
EOF

log "Updating CrowdSec hub"
cscli hub update || log "Hub update failed"

if [ -n "${CROWDSEC_COLLECTIONS:-}" ]; then
  if [ ! -f /var/lib/crowdsec/data/.collections ]; then
    log "Ensuring collections: ${CROWDSEC_COLLECTIONS}"
    printf '%s' "${CROWDSEC_COLLECTIONS}" | tr ',; ' '\n' | while IFS= read -r collection; do
      [ -z "$collection" ] && continue
      cscli collections install "$collection" || log "Skipping collection '$collection' (already present?)"
    done
    touch /var/lib/crowdsec/data/.collections
  else
    log "Collections already processed"
  fi
fi

if [ -n "${CROWDSEC_ENROLL_KEY:-}" ]; then
  if [ ! -f /var/lib/crowdsec/data/.enrolled ]; then
    log "Attempting enrollment"
    if cscli console enroll --key "${CROWDSEC_ENROLL_KEY}" ${CROWDSEC_ENROLL_INSTANCE_ID:+--instance-name ${CROWDSEC_ENROLL_INSTANCE_ID}}; then
      touch /var/lib/crowdsec/data/.enrolled
    else
      log "Enrollment failed"
    fi
  else
    log "Enrollment already completed"
  fi
fi

if [ -n "${CROWDSEC_LAPI_DEFAULT_PASSWORD:-}" ]; then
  if [ ! -f /var/lib/crowdsec/data/.lapi-password ]; then
    log "Setting LAPI password"
    if cscli machines add --auto --password "${CROWDSEC_LAPI_DEFAULT_PASSWORD}"; then
      touch /var/lib/crowdsec/data/.lapi-password
    else
      log "Unable to update LAPI password"
    fi
  else
    log "LAPI password already set"
  fi
fi

log "Starting crowdsec service"
exec /docker-entrypoint.sh "$@"
