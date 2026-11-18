"""Migration 20261118_0003 and shared helpers for the SSP usability pass.

Feature 20261118-144354-ssp-metadata-interconnections-adr (Task 2).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from werkzeug.datastructures import MultiDict
from wtforms import Form, StringField
from wtforms.validators import ValidationError

from scaffold.apps.ssp.forms import validate_external_url

_MIGRATION = Path(__file__).resolve().parents[1] / "migrations/versions/20261118_0003_ssp_usability_pass.py"

# Minimal pre-migration shape of the tables the revision touches (SQLite).
_PRE_SCHEMA = [
    "CREATE TABLE users (id INTEGER PRIMARY KEY)",
    "CREATE TABLE bia_context_scope (id INTEGER PRIMARY KEY, name TEXT NOT NULL, interfaces TEXT)",
    "CREATE TABLE ssp_plans (id INTEGER PRIMARY KEY, context_scope_id INTEGER NOT NULL "
    "REFERENCES bia_context_scope(id), laws_regulations TEXT, monitoring_frequency VARCHAR(100))",
    "CREATE TABLE ssp_interconnections (id INTEGER PRIMARY KEY, ssp_id INTEGER NOT NULL "
    "REFERENCES ssp_plans(id), system_name VARCHAR(255) NOT NULL, sort_order INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE ssp_poam_items (id INTEGER PRIMARY KEY, ssp_id INTEGER NOT NULL REFERENCES ssp_plans(id), "
    "weakness_description TEXT NOT NULL)",
    "CREATE TABLE adr_records (id INTEGER PRIMARY KEY, ssp_id INTEGER NOT NULL REFERENCES ssp_plans(id), "
    "title VARCHAR(255) NOT NULL, status VARCHAR(10) NOT NULL, context TEXT NOT NULL, decision TEXT NOT NULL)",
]


def _load_migration():
    spec = importlib.util.spec_from_file_location("mig_20261118_0003", _MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(conn, fn):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    with Operations.context(MigrationContext.configure(conn)):
        fn()


@pytest.fixture
def migrated():
    mig = _load_migration()
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        for statement in _PRE_SCHEMA:
            conn.execute(sa.text(statement))
        conn.execute(sa.text(
            "INSERT INTO bia_context_scope (id, name, interfaces) VALUES "
            "(1, 'Payroll', 'HR System; Bank API\n  hr   system '), (2, 'Portal', NULL)"
        ))
        conn.execute(sa.text(
            "INSERT INTO ssp_plans (id, context_scope_id, monitoring_frequency) VALUES "
            "(1, 1, 'Monthly'), (2, 2, '  monthly '), (3, 2, 'Quarterly'), (4, 2, '   '), (5, 2, NULL)"
        ))
        conn.execute(sa.text(
            "INSERT INTO ssp_interconnections (ssp_id, system_name) VALUES "
            "(1, 'HR System'), (1, 'bank  api'), (1, 'Legacy FTP')"
        ))
        conn.execute(sa.text(
            "INSERT INTO adr_records (ssp_id, title, status, context, decision) VALUES (1, 'TLS', 'accepted', 'c', 'd')"
        ))
        _run(conn, mig.upgrade)
    yield mig, engine
    engine.dispose()


def test_frequencies_seeded_once_per_normalised_value(migrated):
    _mig, engine = migrated
    with engine.connect() as conn:
        options = conn.execute(sa.text("SELECT id, kind, name FROM ssp_options ORDER BY id")).fetchall()
        plans = dict(conn.execute(sa.text("SELECT id, monitoring_frequency_id FROM ssp_plans")).fetchall())
        plan_columns = {c["name"] for c in sa.inspect(conn).get_columns("ssp_plans")}

    assert [(kind, name) for _id, kind, name in options] == [
        ("monitoring_frequency", "Monthly"),
        ("monitoring_frequency", "Quarterly"),
    ]
    monthly, quarterly = options[0][0], options[1][0]
    assert plans == {1: monthly, 2: monthly, 3: quarterly, 4: None, 5: None}
    assert "monitoring_frequency" not in plan_columns
    assert {"monitoring_frequency_id", "adr_register_url", "laws_regulations"} <= plan_columns


def test_interconnections_matching_bia_are_backfilled_as_bia(migrated):
    _mig, engine = migrated
    with engine.connect() as conn:
        rows = dict(conn.execute(sa.text("SELECT system_name, source FROM ssp_interconnections")).fetchall())

    assert rows == {"HR System": "bia", "bank  api": "bia", "Legacy FTP": "manual"}


def test_adr_and_poam_columns(migrated):
    _mig, engine = migrated
    with engine.connect() as conn:
        adr = {c["name"]: c for c in sa.inspect(conn).get_columns("adr_records")}
        poam = {c["name"] for c in sa.inspect(conn).get_columns("ssp_poam_items")}
        conn.execute(sa.text(
            "INSERT INTO adr_records (ssp_id, title, status, external_url) VALUES (1, 'Link only', 'proposed', 'https://x')"
        ))

    assert adr["context"]["nullable"] is True and adr["decision"]["nullable"] is True
    assert {"external_url", "status_before_supersede"} <= set(adr)
    assert "jira_url" in poam


def test_downgrade_restores_frequency_text_and_drops_new_objects(migrated):
    mig, engine = migrated
    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO adr_records (ssp_id, title, status, external_url) VALUES (1, 'Link only', 'proposed', 'https://x')"
        ))
        _run(conn, mig.downgrade)
        plans = dict(conn.execute(sa.text("SELECT id, monitoring_frequency FROM ssp_plans")).fetchall())
        tables = set(sa.inspect(conn).get_table_names())
        link_only = conn.execute(sa.text("SELECT context, decision FROM adr_records WHERE title = 'Link only'")).one()

    assert plans == {1: "Monthly", 2: "Monthly", 3: "Quarterly", 4: None, 5: None}
    assert not {"ssp_options", "ssp_plan_laws"} & tables
    assert tuple(link_only) == ("", "")


# --- validate_external_url -----------------------------------------------------


class _UrlForm(Form):
    url = StringField(validators=[validate_external_url])


@pytest.fixture
def i18n_app(app):
    """conftest's app (includes the SSP module) with a request context for translations."""
    with app.test_request_context():
        yield app


@pytest.mark.parametrize(
    "value",
    ["https://jira.example.com/browse/SEC-1", "http://intranet/adr", "HTTPS://Confluence.example.com/x?y=1#z"],
)
def test_valid_urls_pass(i18n_app, value):
    form = _UrlForm(MultiDict({"url": f"  {value}  "}))
    assert form.validate(), form.errors
    assert form.url.data == value


@pytest.mark.parametrize(
    "value",
    ["javascript:alert(1)", "ftp://files.example.com/a", "www.example.com", "https://", "https://exa mple.com"],
)
def test_unsafe_or_relative_urls_rejected(i18n_app, value):
    form = _UrlForm(MultiDict({"url": value}))
    assert not form.validate()
    assert [str(e) for e in form.errors["url"]] == ["Enter a full web address starting with http:// or https://."]


def test_too_long_url_rejected(i18n_app):
    form = _UrlForm(MultiDict({"url": "https://example.com/" + "a" * 490}))
    assert not form.validate()
    assert [str(e) for e in form.errors["url"]] == ["The web address may be at most 500 characters."]


def test_empty_url_passes_as_none(i18n_app):
    form = _UrlForm(MultiDict({"url": "   "}))
    assert form.validate()
    assert form.url.data is None


def test_validator_raises_validation_error(i18n_app):
    class Field:
        data = "javascript:x"

    with pytest.raises(ValidationError):
        validate_external_url(None, Field())
