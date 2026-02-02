FROM  python:3.13-slim 

ENV PYTHONUNBUFFERED=1

RUN apt-get update \
  && apt-get install -y --no-install-recommends postgresql-client ca-certificates curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY docker/restore/entrypoint.sh /app/entrypoint.sh
COPY docker/restore/restore_db.py /app/restore_db.py

RUN pip install --no-cache-dir docker \
  && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
