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


class InvalidBackupKey(Exception):
    """No key decrypted the data and at least one key was not a valid Fernet key.

    Deliberately not a ValueError: callers treat ValueError as "unsupported
    backup format". The message never contains key material.
    """


def normalize_key(key: str) -> str:
    """Repair common copy-paste damage to a Fernet key.

    Removes all whitespace, one matching pair of surrounding quotes, and
    restores missing '=' padding. Standard base64 ('+', '/') is not converted.
    """
    key = "".join(key.split())
    if len(key) >= 2 and key[0] == key[-1] and key[0] in "'\"":
        key = key[1:-1]
    return key + "=" * (-len(key) % 4)


def try_decrypt(data: bytes, keys: list[str]) -> bytes:
    """Try each key in order and return the bytes from the first that works.

    Empty or None keys are skipped; data is never returned undecrypted.
    Raises InvalidBackupKey when no key worked and any key was malformed,
    otherwise InvalidToken.
    """
    saw_invalid_key = False
    for key in keys:
        if not key:
            continue
        try:
            fernet = Fernet(normalize_key(key).encode())
        except ValueError:
            saw_invalid_key = True
            continue
        try:
            return fernet.decrypt(data)
        except InvalidToken:
            continue
    if saw_invalid_key:
        raise InvalidBackupKey("The encryption key is not a valid backup key.")
    raise InvalidToken("No key succeeded in decrypting the backup.")
