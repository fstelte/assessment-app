"""Helpers for WebAuthn passkey registration and authentication."""

from __future__ import annotations

import base64
import json
from typing import Tuple

import webauthn
from webauthn.helpers import (
    options_to_json,
    parse_authentication_credential_json,
    parse_registration_credential_json,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from ..identity.models import PasskeyCredential, User


def _rp_id(config: dict) -> str:
    configured = config.get("WEBAUTHN_RP_ID")
    if configured:
        return configured
    server_name = config.get("SERVER_NAME") or "localhost"
    return server_name.split(":")[0]


def _rp_name(config: dict) -> str:
    return config.get("WEBAUTHN_RP_NAME") or config.get("MFA_ISSUER_NAME", "Scaffold Platform")


def _origin(config: dict) -> str:
    explicit = config.get("WEBAUTHN_ORIGIN")
    if explicit:
        return explicit
    server_name = config.get("SERVER_NAME") or "localhost"
    if ":" not in server_name:
        return f"https://{server_name}"
    host, port = server_name.rsplit(":", 1)
    if port == "80":
        return f"http://{host}"
    return f"https://{server_name}"


def challenge_to_session(challenge: bytes) -> str:
    """Encode a challenge bytes object for safe storage in a Flask session."""
    return base64.b64encode(challenge).decode()


def challenge_from_session(encoded: str) -> bytes:
    """Decode a challenge previously stored via challenge_to_session."""
    return base64.b64decode(encoded)


def begin_passkey_registration(user: User, config: dict) -> Tuple[str, bytes]:
    """Return (options_json_str, challenge_bytes) for a passkey registration ceremony."""
    exclude = [
        PublicKeyCredentialDescriptor(id=cred.credential_id)
        for cred in (user.passkey_credentials or [])
    ]
    options = webauthn.generate_registration_options(
        rp_id=_rp_id(config),
        rp_name=_rp_name(config),
        user_id=str(user.id).encode(),
        user_name=user.email,
        user_display_name=user.full_name,
        exclude_credentials=exclude,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    return options_to_json(options), options.challenge


def complete_passkey_registration(
    credential_json_str: str, challenge: bytes, config: dict
) -> webauthn.VerifiedRegistration:
    """Verify a passkey registration response and return the verification result."""
    credential = parse_registration_credential_json(credential_json_str)
    return webauthn.verify_registration_response(
        credential=credential,
        expected_challenge=challenge,
        expected_rp_id=_rp_id(config),
        expected_origin=_origin(config),
    )


def begin_passkey_authentication(user: User, config: dict) -> Tuple[str, bytes]:
    """Return (options_json_str, challenge_bytes) for a passkey authentication ceremony."""
    allow = [
        PublicKeyCredentialDescriptor(id=cred.credential_id)
        for cred in (user.passkey_credentials or [])
    ]
    options = webauthn.generate_authentication_options(
        rp_id=_rp_id(config),
        allow_credentials=allow,
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    return options_to_json(options), options.challenge


def complete_passkey_authentication(
    credential_json_str: str,
    challenge: bytes,
    passkey: PasskeyCredential,
    config: dict,
) -> webauthn.VerifiedAuthentication:
    """Verify a passkey authentication assertion."""
    credential = parse_authentication_credential_json(credential_json_str)
    return webauthn.verify_authentication_response(
        credential=credential,
        expected_challenge=challenge,
        expected_rp_id=_rp_id(config),
        expected_origin=_origin(config),
        credential_public_key=passkey.public_key,
        credential_current_sign_count=passkey.sign_count,
        require_user_verification=False,
    )


def find_passkey_by_raw_id(user: User, raw_id: bytes) -> PasskeyCredential | None:
    """Find a registered passkey for the user matching the given credential raw_id."""
    for cred in (user.passkey_credentials or []):
        if cred.credential_id == raw_id:
            return cred
    return None


def parse_auth_credential_raw_id(credential_json_str: str) -> bytes:
    """Parse a WebAuthn authentication credential JSON and return its raw credential ID bytes."""
    credential = parse_authentication_credential_json(credential_json_str)
    return credential.raw_id
