# syntax=docker/dockerfile:1
FROM python:3.11-slim

ARG POETRY_VERSION=1.8.3
ARG INSTALL_DEV=false
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PATH="${POETRY_HOME}/bin:${PATH}" \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml poetry.lock* ./
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        poetry install --with dev --no-root; \
    else \
        poetry install --no-root; \
    fi

COPY . .

EXPOSE 5000
ENV FLASK_ENV=production \
    FLASK_APP=autoapp

CMD ["flask", "--app", "autoapp", "run", "--host=0.0.0.0", "--port=5000"]
