#!/bin/sh
set -euo pipefail

log() {
  printf '[crowdsec-bouncer] %s\n' "$*" >&2
}

normalize_bool() {
  case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

if [ -z "${CROWDSEC_BOUNCER_API_KEY:-}" ]; then
  log "CROWDSEC_BOUNCER_API_KEY is empty; sleeping to avoid crash"
  sleep infinity
fi

CROWDSEC_BOUNCER_CONFIG="/etc/crowdsec/bouncer.yaml"

blacklist_ipv6="${CROWDSEC_FIREWALL_BOUNCER_IPSET_V6:-crowdsec6-blacklists}"
if normalize_bool "${CROWDSEC_DISABLE_IPV6:-true}"; then
  blacklist_ipv6=""
fi

cat >"$CROWDSEC_BOUNCER_CONFIG" <<EOF
api_url: "${CROWDSEC_BOUNCER_API_URL:-http://127.0.0.1:8080/}"
api_key: "${CROWDSEC_BOUNCER_API_KEY}"
log_level: "${CROWDSEC_BOUNCER_LOG_LEVEL:-info}"
mode: "${CROWDSEC_FIREWALL_BOUNCER_MODE:-iptables}"
update_frequency: "10s"
daemon: false
pid_dir: /var/run/
log_dir: /var/log/
blacklists_ipv4: "${CROWDSEC_FIREWALL_BOUNCER_IPSET:-crowdsec-blacklists}"
blacklists_ipv6: "${blacklist_ipv6}"
iptables:
  chain: input
  set_name: "${CROWDSEC_FIREWALL_BOUNCER_IPSET:-crowdsec-blacklists}"
EOF

log "Launching firewall bouncer"
exec /usr/local/bin/crowdsec-firewall-bouncer -c /etc/crowdsec/bouncer.yaml "$@"
