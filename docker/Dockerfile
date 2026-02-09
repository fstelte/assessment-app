# syntax=docker/dockerfile:1
FROM  python:3.13-slim  AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=2.2.1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq5 libpq-dev ca-certificates curl postgresql-client libxml2-dev libxmlsec1-dev libxmlsec1-openssl pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && pip install "poetry==$POETRY_VERSION" \
    && poetry config virtualenvs.create false
WORKDIR /app

COPY pyproject.toml poetry.lock README.md /app/
RUN poetry install --only main --no-interaction --no-ansi --no-root

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
