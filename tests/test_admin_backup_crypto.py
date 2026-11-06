"""Tests for restore-key normalization and failure classification in backup_crypto."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet, InvalidToken

from scaffold.apps.admin.backup_crypto import (
    InvalidBackupKey,
    encrypt_bytes,
    normalize_key,
    try_decrypt,
)

PAYLOAD = b"backup-bytes"


@pytest.fixture
def key() -> str:
    k = Fernet.generate_key().decode()
    assert k.endswith("=")
    return k


@pytest.fixture
def blob(key) -> bytes:
    return encrypt_bytes(PAYLOAD, key)


class TestNormalizeKey:
    def test_valid_key_unchanged(self, key):
        assert normalize_key(key) == key

    def test_restores_missing_padding(self, key):
        assert normalize_key(key.rstrip("=")) == key

    def test_strips_whitespace_and_quotes(self, key):
        assert normalize_key(f'  "{key}"\n') == key
        assert normalize_key(f"'{key}'") == key

    def test_removes_internal_line_break(self, key):
        assert normalize_key(key[:20] + "\n" + key[20:]) == key


class TestTryDecrypt:
    def test_right_key(self, key, blob):
        assert try_decrypt(blob, [key]) == PAYLOAD

    def test_right_key_without_padding(self, key, blob):  # scenario 1
        assert try_decrypt(blob, [key.rstrip("=")]) == PAYLOAD

    def test_right_key_with_spaces_or_quotes(self, key, blob):  # scenario 7
        assert try_decrypt(blob, [f'  "{key}" ']) == PAYLOAD

    def test_right_key_with_line_break(self, key, blob):  # scenario 11
        assert try_decrypt(blob, [key[:20] + "\r\n" + key[20:]]) == PAYLOAD

    def test_invalid_key_raises_invalid_backup_key(self, blob):
        with pytest.raises(InvalidBackupKey) as exc:
            try_decrypt(blob, ["my-passphrase"])
        assert "my-passphrase" not in str(exc.value)  # scenario 10

    def test_wrong_valid_key_raises_invalid_token(self, blob):
        other = Fernet.generate_key().decode()
        with pytest.raises(InvalidToken) as exc:
            try_decrypt(blob, [other])
        assert other not in str(exc.value)  # scenario 10

    def test_invalid_then_right_key_succeeds(self, key, blob):  # scenario 8
        assert try_decrypt(blob, ["my-passphrase", key]) == PAYLOAD

    @pytest.mark.parametrize("keys", [[], [None], [""]])
    def test_no_usable_key_raises_invalid_token(self, blob, keys):
        with pytest.raises(InvalidToken):
            try_decrypt(blob, keys)

    def test_never_returns_ciphertext(self, blob):
        with pytest.raises(InvalidToken):
            try_decrypt(blob, [None])

    def test_invalid_backup_key_is_not_value_error(self):
        assert not issubclass(InvalidBackupKey, ValueError)
