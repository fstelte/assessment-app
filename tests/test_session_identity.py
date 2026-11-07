"""Restore-safe session identity (decision 20261107-0848, design 20261107-restore-session-identity)."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import sqlalchemy as sa
from flask import session
from flask_login import current_user
from flask_login.utils import encode_cookie

from scaffold.apps.auth.flow import get_enrolment_user, get_pending_user
from scaffold.apps.identity.models import User, UserStatus
from scaffold.extensions import db

PROFILE = "/auth/profile"


def _make_user(email: str) -> User:
    user = User()
    user.email = email
    user.status = UserStatus.ACTIVE
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


def _sign_in(client, token: str) -> None:
    with client.session_transaction() as sess:
        sess["_user_id"] = token
        sess["_fresh"] = True


def _whoami(client) -> str | None:
    """Request a login-protected page and return who Flask-Login loaded (None = anonymous)."""
    with client:  # keep the request context so current_user is still readable afterwards
        resp = client.get(PROFILE)
        if resp.status_code != 200 or not current_user.is_authenticated:
            return None
        return current_user.email


def test_session_token_logs_in(client, active_user):
    _sign_in(client, active_user.get_id())
    assert _whoami(client) == "user@example.com"


def test_numeric_user_id_is_anonymous(client, active_user):
    _sign_in(client, str(active_user.id))  # what pre-migration cookies contain
    assert _whoami(client) is None


def test_reassigned_ids_never_log_in_as_someone_else(client):
    """SC-001: a restore gives A's id to B; A's browser is A or anonymous, never B."""
    alice, bob = _make_user("alice@example.com"), _make_user("bob@example.com")
    _sign_in(client, alice.get_id())
    assert _whoami(client) == "alice@example.com"

    # Simulated restore: each row now holds the *other* person, tokens follow the person.
    a_token, b_token = alice.session_token, bob.session_token
    for i, user in enumerate((alice, bob)):  # park both rows first: email and token are unique
        user.email, user.session_token = f"tmp{i}@example.com", str(i) * 64
        db.session.commit()
    bob.email, bob.session_token = "alice@example.com", a_token
    db.session.commit()
    alice.email, alice.session_token = "bob@example.com", b_token
    db.session.commit()
    assert _whoami(client) == "alice@example.com"  # same person, different row id

    for user in (alice, bob):  # the restore rotates every token
        user.rotate_session_token()
    db.session.commit()
    assert _whoami(client) is None


def test_remember_cookie_stops_working_after_rotation(app, client, active_user):
    """SC-001 for remember-me: the cookie carries the token, not the id."""
    old_cookie = encode_cookie(active_user.get_id())
    client.set_cookie("remember_token", old_cookie)
    assert _whoami(client) == "user@example.com"

    numeric = app.test_client()
    numeric.set_cookie("remember_token", encode_cookie(str(active_user.id)))
    assert _whoami(numeric) is None  # a remember cookie from before the migration

    active_user.rotate_session_token()
    db.session.commit()
    stale = app.test_client()  # no session, only the remember cookie from before the rotation
    stale.set_cookie("remember_token", old_cookie)
    assert _whoami(stale) is None


def test_pending_mfa_steps_follow_the_token(app, active_user):
    """C1: half-finished MFA/passkey steps can't be redirected to another user."""
    with app.test_request_context():
        session["mfa_enroll_user_id"] = active_user.get_id()
        session["mfa_pending_user_id"] = active_user.get_id()
        assert get_enrolment_user() is active_user
        assert get_pending_user() is active_user

        active_user.rotate_session_token()
        db.session.commit()
        assert get_enrolment_user() is None
        assert get_pending_user() is None

        session["mfa_enroll_user_id"] = active_user.id  # numeric id from an old session
        assert get_enrolment_user() is None


def test_migration_backfills_unique_hex_tokens():
    path = Path(__file__).resolve().parents[1] / "migrations/versions/20261107_0001_users_session_token.py"
    spec = importlib.util.spec_from_file_location("mig_20261107_0001", path)
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)"))
        conn.execute(sa.text("INSERT INTO users (email) VALUES ('a@x'), ('b@x'), ('c@x')"))
        with Operations.context(MigrationContext.configure(conn)):
            mig.upgrade()
        tokens = [r[0] for r in conn.execute(sa.text("SELECT session_token FROM users"))]
        cols = {c["name"]: c for c in sa.inspect(conn).get_columns("users")}
        indexes = sa.inspect(conn).get_indexes("users")

    assert len(set(tokens)) == 3 and all(re.fullmatch(r"[0-9a-f]{64}", t) for t in tokens)
    assert cols["session_token"]["nullable"] is False
    assert any(ix["column_names"] == ["session_token"] and ix["unique"] for ix in indexes)
