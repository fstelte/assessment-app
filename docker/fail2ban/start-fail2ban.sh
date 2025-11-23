#!/bin/sh
set -euo pipefail

log() {
  printf '[fail2ban] %s\n' "$*" >&2
}

CONFIG_ROOT="/data/jail.d"
mkdir -p "$CONFIG_ROOT"

cat >/data/jail.d/99-scaffold-nginx.local <<EOF
[DEFAULT]
bantime = ${FAIL2BAN_BANTIME:-3600}
findtime = ${FAIL2BAN_FINDTIME:-600}
maxretry = ${FAIL2BAN_MAXRETRY:-5}
ignoreip = ${FAIL2BAN_IGNORE_IPS:-127.0.0.1/8}
backend = auto

[nginx-http-auth]
enabled = true
port     = http,https
logpath  = ${FAIL2BAN_NGINX_ERROR_LOG:-/var/log/nginx/error.log}
backend  = auto

[nginx-botsearch]
enabled = ${FAIL2BAN_BOTSEARCH_ENABLED:-true}
port     = http,https
logpath  = ${FAIL2BAN_NGINX_ACCESS_LOG:-/var/log/nginx/access.log}
backend  = auto
EOF

log "Starting fail2ban-server"
exec /usr/bin/fail2ban-server "$@"
