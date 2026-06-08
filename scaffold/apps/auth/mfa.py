"""Helpers for managing TOTP-based multi-factor authentication."""

from __future__ import annotations

import base64
import binascii
import os
import re
from dataclasses import dataclass

import pyotp
from cryptography.fernet import InvalidToken

from ...core.encryption import _load_fernet


_FERNET_PREFIX = "gAAAAA"
_SECRET_SANITIZER = re.compile(r"[\s-]+")


def normalize_secret(secret: str | None) -> str:
    """Unwrap legacy nested encryption and normalize user-facing formatting."""

    if secret is None:
        return ""

    candidate = secret.strip()
    if not candidate:
        return ""

    try:
        fernet = _load_fernet()
    except RuntimeError:
        fernet = None

    for _ in range(3):
        if fernet is None or not candidate.startswith(_FERNET_PREFIX):
            break
        try:
            candidate = fernet.decrypt(candidate.encode()).decode().strip()
        except (InvalidToken, UnicodeDecodeError):
            break

    return _SECRET_SANITIZER.sub("", candidate).upper()


def generate_base32_secret(length: int = 32) -> str:
    """Create a random base32-encoded secret compatible with authenticator apps."""

    raw = os.urandom(length)
    return base64.b32encode(raw).decode("utf-8")


@dataclass
class MFAProvisioning:
    secret: str
    uri: str


def build_provisioning(email: str, issuer: str, secret: str | None = None) -> MFAProvisioning:
    """Generate the TOTP provisioning URI and secret for a user."""

    secret_value = normalize_secret(secret) if secret is not None else generate_base32_secret()
    totp = pyotp.TOTP(secret_value)
    uri = totp.provisioning_uri(name=email, issuer_name=issuer)
    return MFAProvisioning(secret=secret_value, uri=uri)


def validate_token(secret: str, token: str, window: int = 1) -> bool:
    """Verify a TOTP token allowing a small leeway window."""

    if not token:
        return False

    sanitized = token.replace(" ", "")
    normalized_secret = normalize_secret(secret)
    if not normalized_secret:
        return False

    totp = pyotp.TOTP(normalized_secret)
    try:
        return totp.verify(sanitized, valid_window=window)
    except (binascii.Error, TypeError):
        return False
