from __future__ import annotations

import sqlalchemy as sa
import pyotp

from scaffold.apps.auth.mfa import build_provisioning, generate_base32_secret, normalize_secret, validate_token
from scaffold.apps.identity.models import MFASetting, User, UserStatus
from scaffold.core.encryption import EncryptedString
from scaffold.extensions import db


def _make_user(email: str) -> User:
    user = User()
    user.email = email
    user.status = UserStatus.ACTIVE
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


def test_validate_token_accepts_double_encrypted_secret():
    secret = generate_base32_secret()
    encrypted_secret = EncryptedString().process_bind_param(secret, None)
    token = pyotp.TOTP(secret).now()

    assert normalize_secret(encrypted_secret) == secret
    assert validate_token(encrypted_secret, token) is True


def test_validate_token_rejects_malformed_secret_without_crashing():
    assert validate_token("not-a-base32-secret", "123456") is False


def test_build_provisioning_uses_normalized_secret():
    secret = generate_base32_secret()
    encrypted_secret = EncryptedString().process_bind_param(secret, None)

    provisioning = build_provisioning("user@example.com", "Scaffold", secret=encrypted_secret)

    assert provisioning.secret == secret
    assert f"secret={secret}" in provisioning.uri


def test_encrypt_existing_secrets_encrypts_only_plaintext_rows(app):
    with app.app_context():
        user = _make_user("mfa-cli@example.com")
        secret = generate_base32_secret()
        db.session.execute(
            sa.text(
                """
                INSERT INTO mfa_settings (user_id, secret, enabled, backup_codes, created_at, updated_at)
                VALUES (:user_id, :secret, 1, :backup_codes, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "user_id": user.id,
                "secret": secret,
                "backup_codes": '["alpha","bravo"]',
            },
        )
        db.session.commit()

        runner = app.test_cli_runner()
        result = runner.invoke(args=["encrypt-existing-secrets"])

        assert result.exit_code == 0
        assert "Encrypted: 1 MFASetting record(s)." in result.output

        mfa = db.session.scalar(sa.select(MFASetting).where(MFASetting.user_id == user.id))
        assert mfa is not None
        assert mfa.secret == secret
        assert mfa.backup_codes == ["alpha", "bravo"]

        raw_row = db.session.execute(
            sa.text("SELECT secret, backup_codes FROM mfa_settings WHERE user_id = :user_id"),
            {"user_id": user.id},
        ).mappings().one()

        assert raw_row["secret"].startswith("gAAAAA")
        assert raw_row["backup_codes"].startswith("gAAAAA")