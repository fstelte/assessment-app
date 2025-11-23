# Nginx Configuration Examples

The active `docker/nginx/nginx.conf` handles runtime toggles (Certbot, CrowdSec, etc.). Use the snippets below when you need to craft a static configuration for reference or for environments that do not rely on the entrypoint automation.

## Behind an Existing Reverse Proxy (no Certbot / CrowdSec)

```nginx
worker_processes 1;

error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
  worker_connections 1024;
}

http {
  include       /etc/nginx/mime.types;
  default_type  application/octet-stream;

  sendfile on;
  keepalive_timeout 65;

  upstream app_backend {
    server web:8000;
    keepalive 16;
  }

  server {
    # Only expose the internal port that the upstream proxy forwards to.
    listen 8000;
    listen [::]:8000;

    server_name _;

    error_page 500 502 503 504 =503 /maintenance.html;

    location = /maintenance.html {
      alias /usr/share/nginx/html/maintenance/maintenance.html;
      internal;
      add_header Cache-Control "no-store";
    }

    location / {
      proxy_pass http://app_backend;
      proxy_http_version 1.1;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
      proxy_intercept_errors on;
    }
  }
}
```

Fail2Ban only tails the access/error logs; no additional `include` is required. Ensure the log volume is mounted at `/var/log/nginx` so the container can read `access.log` and `error.log`. When traffic arrives through another reverse proxy, let that external layer terminate TLS and expose only the internal port here (usually 8000).

## Public-Facing Gateway (Certbot, CrowdSec, optional HTTPS redirect)

```nginx
worker_processes 1;

env CERTBOT_ENABLED;
env CERTBOT_FORCE_HTTPS;
env CERTBOT_PRIMARY_DOMAIN;

env CROWDSEC_BOUNCER_ENABLED;

env CERTBOT_TLS_READY;

error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
  worker_connections 1024;
}

http {
  include       /etc/nginx/mime.types;
  default_type  application/octet-stream;
  include       /etc/nginx/conf.d/*.conf;        # Certbot TLS listener rendered by entrypoint
  include       /etc/nginx/crowdsec/*.conf;      # (Optional) CrowdSec bouncer snippets

  map $CERTBOT_ENABLED $certbot_tls_enabled {
    default 0;
    "1" 1;
    "true" 1;
    "TRUE" 1;
    "True" 1;
    "yes" 1;
    "on" 1;
  }

  map $CERTBOT_FORCE_HTTPS $certbot_force_https {
    default 0;
    "1" 1;
    "true" 1;
    "TRUE" 1;
    "True" 1;
    "yes" 1;
    "on" 1;
  }

  map "$certbot_tls_enabled:$certbot_force_https" $certbot_redirect_https {
    default 0;
    "1:1" 1;
  }

  sendfile on;
  keepalive_timeout 65;

  upstream app_backend {
    server web:8000;
    keepalive 16;
  }

  server {
    listen 8000;
    listen [::]:8000;
    listen 80;
    listen [::]:80;

    server_name _;

    error_page 500 502 503 504 =503 /maintenance.html;

    location = /maintenance.html {
      alias /usr/share/nginx/html/maintenance/maintenance.html;
      internal;
      add_header Cache-Control "no-store";
    }

    location ^~ /.well-known/acme-challenge/ {
      root /var/www/certbot;
      default_type "text/plain";
      try_files $uri =404;
    }

    location / {
      set $certbot_tls_ready 0;
      if (-f /etc/nginx/conf.d/90-certbot-tls.conf) {
        set $certbot_tls_ready 1;
      }
      if ($certbot_redirect_https$certbot_tls_ready = 11) {
        return 308 https://$host$request_uri;
      }
      proxy_pass http://app_backend;
      proxy_http_version 1.1;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
      proxy_intercept_errors on;
    }
  }
}
```

### Notes

- Certbot automation mounts `/etc/nginx/conf.d/90-certbot-tls.conf` when certificates exist; the `include` directive loads that file automatically. The HTTP block only redirects once that file is present.
- CrowdSec attaches bouncer configuration files under `/etc/nginx/crowdsec/*.conf`. Typical snippets add `deny` directives or challenge logic based on the firewall bouncer decisions.
- Fail2Ban requires no Nginx modifications, but it does rely on the shared `/var/log/nginx` volume to read request logs.

These examples provide a baseline if you need to handcraft configurations outside the automated entrypoint logic.
