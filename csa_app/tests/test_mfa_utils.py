"""Unit tests for MFA helper utilities."""

from __future__ import annotations

import pyotp

from app.auth.mfa import generate_base32_secret, validate_token


def test_generate_base32_secret_returns_valid_secret():
    secret = generate_base32_secret()
    assert isinstance(secret, str)
    assert len(secret) >= 32


def test_validate_token_accepts_spaced_input():
    secret = pyotp.random_base32()
    token = pyotp.TOTP(secret).now()
    spaced_token = f"{token[:3]} {token[3:]}"
    assert validate_token(secret, spaced_token) is True
