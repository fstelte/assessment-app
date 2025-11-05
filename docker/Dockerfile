# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_HOME=/opt/poetry \
    POETRY_VERSION=2.2.1 \
    PATH="/opt/poetry/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq5 libpq-dev ca-certificates curl postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && poetry config virtualenvs.create false

WORKDIR /app

COPY pyproject.toml poetry.lock README.md /app/
RUN poetry install --only main --no-interaction --no-ansi --no-root

COPY . /app

COPY docker/entrypoint.sh /entrypoint.sh
# Ensure entrypoint uses LF endings inside the image (strip CRLF if present on host)
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

ENV FLASK_APP=scaffold:create_app
ENV FLASK_ENV=production

EXPOSE 8000

CMD ["/entrypoint.sh"]
