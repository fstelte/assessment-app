# Nginx Configuration (Public-Facing Gateway)

Use this reference when the gateway container terminates HTTP/HTTPS directly and you rely on the bundled automation for Certbot certificates and CrowdSec enforcement.

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

- Certbot automation mounts `/etc/nginx/conf.d/90-certbot-tls.conf` when certificates exist; the `include` directive loads that file automatically, and HTTP traffic only redirects once the file is present.
- CrowdSec attaches bouncer configuration files under `/etc/nginx/crowdsec/*.conf`. Typical snippets add `deny` directives or challenge logic based on the firewall bouncer decisions.
- Fail2Ban requires no Nginx modifications, but it does rely on the shared `/var/log/nginx` volume to read request logs.