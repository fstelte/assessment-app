# Nginx Configuration (Behind Reverse Proxy)

The gateway container can sit behind an upstream load balancer or reverse proxy that terminates TLS and forwards traffic internally. In that setup the bundled entrypoint logic is often overkill. Use the static configuration below when you want a lightweight proxy that only listens on its internal port.

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

Fail2Ban only tails the access/error logs; no additional `include` is required. Ensure the log volume is mounted at `/var/log/nginx` so the container can read `access.log` and `error.log`.