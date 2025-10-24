"""Reusable helpers orchestrating the combined authentication flow.

This module centralises the shared behaviour that both legacy applications
implemented separately: password logins that seed secure session metadata,
TOTP-based MFA enrolment/verification, and storage of convenience flags in the
session. By reusing these helpers inside the blueprint routes we keep the
control flow declarative and make the security guarantees auditable.
"""

from __future__ import annotations

from datetime import UTC, datetime

from flask import session
from flask_login import login_user

from ...core.security import generate_session_fingerprint
from ...extensions import db
from ..identity.models import MFASetting, User
from .mfa import MFAProvisioning, build_provisioning

_MFA_SESSION_KEYS = ("mfa_pending_user_id", "mfa_enroll_user_id", "mfa_remember_me")


def queue_mfa_verification(user: User, remember: bool) -> None:
    """Flag the current session to require MFA verification."""

    session["mfa_pending_user_id"] = user.id
    session["mfa_remember_me"] = remember


def queue_mfa_enrolment(user: User, remember: bool) -> None:
    """Flag the current session to require MFA enrolment."""

    session["mfa_enroll_user_id"] = user.id
    session["mfa_remember_me"] = remember


def current_remember_me(default: bool = False) -> bool:
    """Return the remember-me flag captured prior to the MFA challenge."""

    return bool(session.get("mfa_remember_me", default))


def get_pending_user() -> User | None:
    """Retrieve the user awaiting MFA verification."""

    user_id = session.get("mfa_pending_user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def get_enrolment_user() -> User | None:
    """Retrieve the user awaiting MFA enrolment."""

    user_id = session.get("mfa_enroll_user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def ensure_mfa_provisioning(user: User, issuer: str) -> MFAProvisioning:
    """Return the provisioning payload, creating or resetting the MFA record."""

    if user.mfa_setting is None:
        provisioning = build_provisioning(user.email, issuer)
        setting = MFASetting()
        setting.secret = provisioning.secret
        setting.enabled = True
        user.mfa_setting = setting
        db.session.add(setting)
    else:
        provisioning = build_provisioning(user.email, issuer, secret=user.mfa_setting.secret)
        user.mfa_setting.enabled = True
        user.mfa_setting.enrolled_at = None
    db.session.commit()
    return provisioning


def clear_mfa_state() -> None:
    """Remove MFA-related state from the session."""

    for key in _MFA_SESSION_KEYS:
        session.pop(key, None)


def finalise_login(user: User, remember: bool) -> None:
    """Complete the login by stamping security metadata and updating the user."""

    now = datetime.now(UTC)
    login_user(user, remember=remember)
    user.last_login_at = now
    db.session.commit()

    session.permanent = True
    session["login_time"] = now.isoformat()
    session["last_activity"] = now.isoformat()
    session["session_fingerprint"] = generate_session_fingerprint()
    clear_mfa_state()