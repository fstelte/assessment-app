
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates curl gnupg lsb-release wget \
  && wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg \
  && echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends postgresql-client-18 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy files from the repository root (build context is set to .. in compose)
COPY docker/backup-db.sh /app/backup-db.sh
COPY docker/backup/entrypoint.sh /app/entrypoint.sh
COPY docker/s3_upload.py /app/s3_upload.py
COPY docker/serve-status.py /app/serve-status.py
COPY docker/healthcheck.sh /app/healthcheck.sh

RUN pip install --no-cache-dir boto3 || true
RUN chmod +x /app/backup-db.sh /app/entrypoint.sh /app/healthcheck.sh

EXPOSE 9090

# Healthcheck uses the status file to decide if backup container is healthy
HEALTHCHECK --interval=60s --timeout=5s --start-period=10s --retries=3 CMD ["/app/healthcheck.sh"]

ENTRYPOINT ["/app/entrypoint.sh"]
