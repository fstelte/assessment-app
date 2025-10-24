"""Helpers for managing TOTP-based multi-factor authentication."""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass

import pyotp


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

    secret_value = secret or generate_base32_secret()
    totp = pyotp.TOTP(secret_value)
    uri = totp.provisioning_uri(name=email, issuer_name=issuer)
    return MFAProvisioning(secret=secret_value, uri=uri)


def validate_token(secret: str, token: str, window: int = 1) -> bool:
    """Verify a TOTP token allowing a small leeway window."""

    if not token:
        return False
    sanitized = token.replace(" ", "")
    totp = pyotp.TOTP(secret)
    return totp.verify(sanitized, valid_window=window)
