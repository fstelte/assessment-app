"""Fernet encryption utilities for admin backup/restore operations."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken


def generate_key() -> str:
    """Generate a new Fernet key, returned as a plain string."""
    return Fernet.generate_key().decode()


def encrypt_bytes(data: bytes, key: str) -> bytes:
    """Encrypt raw bytes with the given Fernet key."""
    return Fernet(key.encode()).encrypt(data)


def decrypt_bytes(data: bytes, key: str) -> bytes:
    """Decrypt Fernet-encrypted bytes. Raises InvalidToken on failure."""
    return Fernet(key.encode()).decrypt(data)


def try_decrypt(data: bytes, keys: list) -> bytes:
    """
    Try each key in order (str or None). Returns decrypted bytes on first success.
    Raises InvalidToken if all keys fail.
    Pass None as a key to return data as-is (unencrypted fallback).
    """
    for key in keys:
        if key is None:
            return data
        try:
            return Fernet(key.encode()).decrypt(data)
        except InvalidToken:
            continue
    raise InvalidToken("No key succeeded in decrypting the backup.")
