#!/bin/sh
set -euo pipefail

normalize_bool() {
  case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

CERTBOT_CONF="/etc/nginx/conf.d/90-certbot-tls.conf"
CERTBOT_DOMAIN="${CERTBOT_PRIMARY_DOMAIN:-}"
CERTBOT_EXTRA_RAW="${CERTBOT_ADDITIONAL_DOMAINS:-}"
CERTBOT_CERT_DIR="/etc/letsencrypt/live/${CERTBOT_DOMAIN}"

mkdir -p /var/www/certbot
rm -f /etc/nginx/conf.d/default.conf

if ! normalize_bool "${CERTBOT_ENABLED:-false}"; then
  rm -f "$CERTBOT_CONF"
  exit 0
fi

if [ -z "$CERTBOT_DOMAIN" ]; then
  echo "[gateway] CERTBOT_ENABLED=true but CERTBOT_PRIMARY_DOMAIN is not set" >&2
  exit 1
fi

server_names="$CERTBOT_DOMAIN"
if [ -n "$CERTBOT_EXTRA_RAW" ]; then
  # Replace commas and newlines with spaces, then squeeze multiple spaces
  CERTBOT_EXTRA_TRIMMED=$(printf '%s' "$CERTBOT_EXTRA_RAW" | tr ',\n\r' '   ' | xargs 2>/dev/null || true)
  if [ -n "$CERTBOT_EXTRA_TRIMMED" ]; then
    server_names="$server_names $CERTBOT_EXTRA_TRIMMED"
  fi
fi

if [ -f "${CERTBOT_CERT_DIR}/fullchain.pem" ] && [ -f "${CERTBOT_CERT_DIR}/privkey.pem" ]; then
  cat >"$CERTBOT_CONF" <<EOF
server {
  listen 443 ssl http2;
  listen [::]:443 ssl http2;
  server_name ${server_names};

  error_page 500 502 503 504 =503 /maintenance.html;

  ssl_certificate ${CERTBOT_CERT_DIR}/fullchain.pem;
  ssl_certificate_key ${CERTBOT_CERT_DIR}/privkey.pem;
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_session_cache shared:SSL:10m;
  ssl_session_timeout 1d;

  location = /maintenance.html {
    alias /usr/share/nginx/html/maintenance/maintenance.html;
    internal;
    add_header Cache-Control "no-store";
  }

  location ^~ /.well-known/acme-challenge/ {
    root /var/www/certbot;
    default_type "text/plain";
    try_files \$uri =404;
  }

  location / {
    proxy_pass http://app_backend;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_intercept_errors on;
  }
}
EOF
else
  rm -f "$CERTBOT_CONF"
  echo "[gateway] Waiting for certificates in ${CERTBOT_CERT_DIR}; HTTPS listener disabled" >&2
fi
