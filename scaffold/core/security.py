"""Session security helpers."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Callable, TypeVar

from flask import current_app, flash, redirect, request, session, url_for
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


def generate_session_fingerprint() -> int:
    """Generate a fingerprint for the current session."""

    user_agent = request.headers.get("User-Agent", "")
    return hash(user_agent)


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
    """Delete all server-side sessions belonging to a user.

    Only has an effect when Flask-Session is using the Redis backend
    (i.e. ``SESSION_TYPE == "redis"``).
    """
    if current_app.config.get("SESSION_TYPE") != "redis":
        return
    try:
        from ..extensions import get_redis

        r = get_redis()
        prefix = current_app.config.get("SESSION_KEY_PREFIX", "session:")
        cursor = 0
        while True:
            cursor, keys = r.scan(cursor, match=f"{prefix}*", count=100)
            for key in keys:
                data = r.get(key)
                if data and f'"_user_id": "{user_id}"'.encode() in (
                    data if isinstance(data, bytes) else data.encode()
                ):
                    r.delete(key)
            if cursor == 0:
                break
    except Exception:
        logger.warning("Failed to invalidate server-side sessions for user %s", user_id, exc_info=True)
