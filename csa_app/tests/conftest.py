"""Pytest fixtures for the application."""

from __future__ import annotations

import os
from typing import Generator

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def app() -> Generator:
    """Create a Flask app bound to an in-memory SQLite database."""
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def postgres_database_uri() -> str | None:
    """Return the Postgres database URI for integration tests if configured."""

    return os.getenv("TEST_DATABASE_URL")


@pytest.fixture()
def postgres_app(postgres_database_uri) -> Generator:
    """Provide an application bound to a Postgres database for integration tests."""

    if not postgres_database_uri:
        pytest.skip("TEST_DATABASE_URL environment variable is not set for Postgres tests.")

    app = create_app("testing")
    app.config.update(SQLALCHEMY_DATABASE_URI=postgres_database_uri)

    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def postgres_client(postgres_app):
    return postgres_app.test_client()
