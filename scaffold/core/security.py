"""Session security helpers."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Callable, TypeVar

from flask import flash, redirect, request, session, url_for
from flask_login import current_user, logout_user

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable[..., object])


def init_session_security(app) -> None:
    """Attach session security checks to the Flask app."""

    @app.before_request
    def check_session_security():  # noqa: D401
        """Validate session fingerprint and activity window."""

        if request.endpoint and (
            request.endpoint.startswith("static")
            or request.endpoint in {"auth.login", "auth.register", "auth.logout", "auth.mfa_enroll", "auth.mfa_verify"}
        ):
            return None

        if not current_user.is_authenticated:
            return None

        if "last_activity" in session:
            last_activity = datetime.fromisoformat(session["last_activity"])
            if last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=UTC)
            if datetime.now(UTC) - last_activity > timedelta(hours=12):
                logout_user()
                session.clear()
                flash("Your session has expired. Please log in again.", "warning")
                return redirect(url_for("auth.login"))

        fingerprint = generate_session_fingerprint()
        stored_fingerprint = session.get("session_fingerprint")
        if stored_fingerprint is not None and stored_fingerprint != fingerprint:
            logout_user()
            session.clear()
            flash("Security violation detected. Please log in again.", "danger")
            return redirect(url_for("auth.login"))

        session.setdefault("session_fingerprint", fingerprint)
        session["last_activity"] = datetime.now(UTC).isoformat()
        session.permanent = True
        return None


def generate_session_fingerprint() -> str:
    """Generate a fingerprint for the current session.

    sha256, not hash(): hash() is randomised per process, which logged everyone
    out on every restart. Stable is only safe now that sessions carry the
    session token instead of the numeric user id (decision 20261107-0848).
    """

    user_agent = request.headers.get("User-Agent", "")
    return hashlib.sha256(user_agent.encode("utf-8")).hexdigest()


def require_fresh_login(max_age_minutes: int = 30) -> Callable[[T], T]:
    """Decorator ensuring the user logged in recently before accessing sensitive actions."""

    def decorator(func: T) -> T:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))

            login_time_iso = session.get("login_time")
            if not login_time_iso:
                return redirect(url_for("auth.reauth", next=request.url))

            login_time = datetime.fromisoformat(login_time_iso)
            if login_time.tzinfo is None:
                login_time = login_time.replace(tzinfo=UTC)
            if datetime.now(UTC) - login_time > timedelta(minutes=max_age_minutes):
                return redirect(url_for("auth.reauth", next=request.url))

            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def invalidate_user_sessions(user_id: int) -> None:
    """End every session and remember-me cookie of a user, with any session backend.

    Rotates the user's session token (decision 20261107-0905); sessions that still
    carry the old token no longer load a user.
    """
    from ..apps.identity.models import User
    from ..extensions import db

    user = db.session.get(User, user_id)
    if user is None:
        return
    user.rotate_session_token()
    db.session.commit()
