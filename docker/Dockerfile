# syntax=docker/dockerfile:1
FROM  python:3.13-slim  AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=2.2.1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq5 libpq-dev ca-certificates curl gnupg lsb-release wget postgresql-client libxml2-dev libxmlsec1-dev libxmlsec1-openssl pkg-config \
    && wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-18 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install "poetry==$POETRY_VERSION" \
    && poetry config virtualenvs.create false
WORKDIR /app

COPY pyproject.toml poetry.lock README.md /app/
RUN poetry install --only main --no-interaction --no-ansi --no-root \
    && playwright install --with-deps chromium \
    && apt-get purge -y libncursesw6 \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

# Generate CSS during build so the image contains the latest styles
RUN python3 scaffold/tailwind_cli.py -i scaffold/static/css/tailwind.css -o scaffold/static/css/app.css \
    && rm -rf /app/.tailwind

COPY docker/entrypoint.sh /entrypoint.sh
# Ensure entrypoint uses LF endings inside the image (strip CRLF if present on host)
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

ENV FLASK_APP=scaffold:create_app
ENV FLASK_ENV=production

EXPOSE 8000

CMD ["/entrypoint.sh"]
