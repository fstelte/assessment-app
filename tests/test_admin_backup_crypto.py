"""Tests for restore-key normalization and failure classification in backup_crypto."""

from __future__ import annotations

import io
from datetime import UTC, datetime

import pytest
from cryptography.fernet import Fernet, InvalidToken

from scaffold.apps.admin.backup_crypto import (
    InvalidBackupKey,
    encrypt_bytes,
    normalize_key,
    try_decrypt,
)
from scaffold.apps.identity.models import Role, User, UserStatus
from scaffold.extensions import db

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


# ---------------------------------------------------------------------------
# Full restore route (/admin/backup/restore)
# ---------------------------------------------------------------------------

DUMP = b"\x1f\x8b fake gzip dump"  # the route doesn't inspect contents
FILENAME = "pg_dump-manual-20261106T070556Z.sql.gz"


@pytest.fixture
def restore_env(app, client, tmp_path):
    """Admin signed in, isolated backup/restore dirs, no configured key."""
    incoming = tmp_path / "incoming"
    app.config.update(
        BACKUP_DIR=str(tmp_path / "backups"),
        RESTORE_WATCH_DIR=str(incoming),
        BACKUP_ENCRYPTION_KEY=None,
    )
    role = Role()
    role.name = "admin"
    user = User()
    user.email = "admin@example.com"
    user.status = UserStatus.ACTIVE
    user.set_password("Password123!")
    user.roles.append(role)
    db.session.add_all([role, user])
    db.session.commit()
    # Password login forces MFA enrolment; authenticate the session directly.
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True
        sess["login_time"] = datetime.now(UTC).isoformat()
    return incoming


def _upload(client, data: bytes, filename: str, key: str = ""):
    return client.post(
        "/admin/backup/restore",
        data={"backup_file": (io.BytesIO(data), filename), "encryption_key": key},
        content_type="multipart/form-data",
    )


class TestFullRestoreRoute:
    def test_key_without_padding_queues_decrypted_file(self, restore_env, client, key):  # scenario 2
        resp = _upload(client, encrypt_bytes(DUMP, key), FILENAME + ".enc", key.rstrip("="))
        assert resp.status_code == 302
        assert (restore_env / FILENAME).read_bytes() == DUMP

    def test_invalid_key_shows_message_not_500(self, restore_env, client, key, caplog):  # scenarios 3, 10
        resp = _upload(client, encrypt_bytes(DUMP, key), FILENAME + ".enc", "my-passphrase")
        assert resp.status_code == 200
        assert b"not a valid backup key" in resp.data
        assert not restore_env.exists()
        assert b"my-passphrase" not in resp.data
        assert "my-passphrase" not in caplog.text

    def test_wrong_key_shows_decrypt_failed(self, restore_env, client, key, caplog):  # scenarios 4, 10
        other = Fernet.generate_key().decode()
        resp = _upload(client, encrypt_bytes(DUMP, key), FILENAME + ".enc", other)
        assert resp.status_code == 200
        assert b"Decryption failed" in resp.data
        assert not restore_env.exists()
        assert other.encode() not in resp.data
        assert other not in caplog.text

    def test_no_key_shows_decrypt_failed(self, restore_env, client, key):  # scenario 5
        resp = _upload(client, encrypt_bytes(DUMP, key), FILENAME + ".enc")
        assert resp.status_code == 200
        assert b"Decryption failed" in resp.data
        assert not restore_env.exists()

    @pytest.mark.parametrize("typed_key", ["", "my-passphrase"])
    def test_unencrypted_upload_unchanged(self, restore_env, client, typed_key):  # scenarios 6, 12
        resp = _upload(client, DUMP, FILENAME, typed_key)
        assert resp.status_code == 302
        assert (restore_env / FILENAME).read_bytes() == DUMP
