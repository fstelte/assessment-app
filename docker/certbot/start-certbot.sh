#!/bin/sh
set -euo pipefail

normalize_bool() {
  case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

LOG_PREFIX="[certbot]"
WEBROOT="/var/www/certbot"
DEFAULT_INTERVAL=43200

mkdir -p "$WEBROOT"

loop_interval="${CERTBOT_RENEW_INTERVAL:-$DEFAULT_INTERVAL}"
if ! printf '%s' "$loop_interval" | grep -Eq '^[0-9]+$'; then
  echo "$LOG_PREFIX Invalid CERTBOT_RENEW_INTERVAL='$loop_interval', falling back to $DEFAULT_INTERVAL" >&2
  loop_interval=$DEFAULT_INTERVAL
fi

while true; do
  if ! normalize_bool "${CERTBOT_ENABLED:-false}"; then
    echo "$LOG_PREFIX Disabled; sleeping for $loop_interval seconds" >&2
    sleep "$loop_interval"
    continue
  fi

  if [ -z "${CERTBOT_EMAIL:-}" ]; then
    echo "$LOG_PREFIX CERTBOT_EMAIL must be set" >&2
    sleep "$loop_interval"
    continue
  fi

  if [ -z "${CERTBOT_PRIMARY_DOMAIN:-}" ]; then
    echo "$LOG_PREFIX CERTBOT_PRIMARY_DOMAIN must be set" >&2
    sleep "$loop_interval"
    continue
  fi

  domain_args="-d ${CERTBOT_PRIMARY_DOMAIN}"
  if [ -n "${CERTBOT_ADDITIONAL_DOMAINS:-}" ]; then
    extras=$(printf '%s' "${CERTBOT_ADDITIONAL_DOMAINS}" | tr ',\n\r' '   ' | xargs 2>/dev/null || true)
    for d in $extras; do
      domain_args="$domain_args -d $d"
    done
  fi

  cert_args="certonly --webroot --webroot-path ${WEBROOT} --non-interactive --agree-tos ${domain_args} --email ${CERTBOT_EMAIL}"
  if normalize_bool "${CERTBOT_STAGING:-false}"; then
    cert_args="$cert_args --staging"
  fi

  if [ -n "${CERTBOT_RSA_KEY_SIZE:-}" ]; then
    if printf '%s' "${CERTBOT_RSA_KEY_SIZE}" | grep -Eq '^[0-9]+$'; then
      cert_args="$cert_args --rsa-key-size ${CERTBOT_RSA_KEY_SIZE}"
    else
      echo "$LOG_PREFIX Ignoring invalid CERTBOT_RSA_KEY_SIZE='${CERTBOT_RSA_KEY_SIZE}'" >&2
    fi
  fi

  target_dir="/etc/letsencrypt/live/${CERTBOT_PRIMARY_DOMAIN}"
  if [ -f "${target_dir}/fullchain.pem" ] && [ -f "${target_dir}/privkey.pem" ]; then
    renew_cmd="renew --webroot --webroot-path ${WEBROOT}"
    if normalize_bool "${CERTBOT_STAGING:-false}"; then
      renew_cmd="$renew_cmd --staging"
    fi
    echo "$LOG_PREFIX Running renewal" >&2
    certbot $renew_cmd || echo "$LOG_PREFIX Renewal failed" >&2
  else
    echo "$LOG_PREFIX Requesting certificates for ${CERTBOT_PRIMARY_DOMAIN}" >&2
    certbot $cert_args || echo "$LOG_PREFIX Initial request failed" >&2
  fi

  sleep "$loop_interval"
done
