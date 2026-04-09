"""Field-level encryption helpers using Fernet symmetric encryption."""

from __future__ import annotations

import json
import os

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator


def _load_fernet() -> MultiFernet:
    """Load one or more Fernet keys from environment variables.

    Supports key rotation via comma-separated FIELD_ENCRYPTION_KEYS.
    The first key is the active encryption key; subsequent keys are used
    for decryption only (rotation support).
    """
    raw = os.environ.get("FIELD_ENCRYPTION_KEYS", "")
    if not raw:
        raise RuntimeError(
            "FIELD_ENCRYPTION_KEYS is not configured. "
            "Generate a key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    keys = [Fernet(k.strip().encode()) for k in raw.split(",") if k.strip()]
    return MultiFernet(keys)


class EncryptedString(TypeDecorator):
    """Transparently encrypted String column (stored as Text)."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        fernet = _load_fernet()
        return fernet.encrypt(value.encode()).decode()

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        fernet = _load_fernet()
        try:
            return fernet.decrypt(value.encode()).decode()
        except InvalidToken:
            # Value is plaintext (pre-encryption migration); return as-is.
            return value


class EncryptedJSON(TypeDecorator):
    """Transparently encrypted JSON column (serialised as string then encrypted)."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect) -> str | None:
        if value is None:
            return None
        fernet = _load_fernet()
        serialized = json.dumps(value)
        return fernet.encrypt(serialized.encode()).decode()

    def process_result_value(self, value: str | None, dialect):
        if value is None:
            return None
        fernet = _load_fernet()
        try:
            decrypted = fernet.decrypt(value.encode()).decode()
        except InvalidToken:
            # Value is plaintext JSON (pre-encryption migration); parse as-is.
            decrypted = value
        return json.loads(decrypted)


class EncryptedBinary(TypeDecorator):
    """Transparently encrypted LargeBinary column (stored as Text)."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: bytes | None, dialect) -> str | None:
        if value is None:
            return None
        fernet = _load_fernet()
        return fernet.encrypt(value).decode()

    def process_result_value(self, value: str | None, dialect) -> bytes | None:
        if value is None:
            return None
        fernet = _load_fernet()
        try:
            return fernet.decrypt(value.encode())
        except InvalidToken:
            # Value is plaintext bytes (pre-encryption migration); return as-is.
            return value.encode()
