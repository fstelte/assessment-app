FROM  python:3.13-slim 

ENV PYTHONUNBUFFERED=1

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates curl gnupg lsb-release wget \
  && wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg \
  && echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends postgresql-client-18 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY docker/restore/entrypoint.sh /app/entrypoint.sh
COPY docker/restore/restore_db.py /app/restore_db.py

RUN pip install --no-cache-dir docker cryptography \
  && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
