"""SAML helpers for Microsoft Entra ID federation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping

from flask import current_app
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.metadata import OneLogin_Saml2_Metadata
from onelogin.saml2.settings import OneLogin_Saml2_Settings


@dataclass(slots=True)
class SamlSettings:
    """Typed container wrapping python3-saml settings."""

    config: Dict[str, Any]
    allowed_group_ids: list[str]
    group_attribute: str
    email_attribute: str
    first_name_attribute: str
    last_name_attribute: str
    display_name_attribute: str
    object_id_attribute: str
    upn_attribute: str
    requested_authn_context: list[str] | bool
    requested_authn_context_comparison: str

    def is_configured(self) -> bool:
        sp = self.config.get("sp", {})
        idp = self.config.get("idp", {})
        has_cert = bool(idp.get("x509cert") or idp.get("x509certMulti"))
        return bool(
            sp.get("entityId")
            and sp.get("assertionConsumerService", {}).get("url")
            and idp.get("entityId")
            and idp.get("singleSignOnService", {}).get("url")
            and has_cert
        )

    def python_saml_settings(self) -> OneLogin_Saml2_Settings:
        return OneLogin_Saml2_Settings(self.config, validate_certificates=False)

    def sp_metadata(self) -> str:
        settings = self.python_saml_settings()
        metadata = settings.get_sp_metadata()
        errors = OneLogin_Saml2_Metadata.validate_metadata(metadata)
        if errors:
            current_app.logger.warning("SAML SP metadata validation warnings: %s", ", ".join(errors))
        return metadata


def build_settings(config: Mapping[str, Any]) -> SamlSettings:
    """Create SAML configuration from Flask settings."""

    def _value(*keys: str, default: str = "") -> str:
        for key in keys:
            raw = config.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
        return default

    def _bool(*keys: str, default: bool = False) -> bool:
        truthy = {"1", "true", "yes", "on"}
        falsy = {"0", "false", "no", "off"}
        for key in keys:
            raw = config.get(key)
            if isinstance(raw, str):
                lowered = raw.strip().lower()
                if lowered in truthy:
                    return True
                if lowered in falsy:
                    return False
            elif isinstance(raw, bool):
                return raw
        return default

    def _list(value: str) -> list[str]:
        return [item.strip().lower() for item in value.split(",") if item.strip()]

    sp_cert = _value("SAML_SP_CERT")
    sp_key = _value("SAML_SP_PRIVATE_KEY")
    requested_authn_context = _parse_requested_authn_context(_value("SAML_REQUESTED_AUTHN_CONTEXT"))
    requested_authn_context_comparison = _value("SAML_REQUESTED_AUTHN_CONTEXT_COMPARISON", default="minimum") or "minimum"

    saml_config: Dict[str, Any] = {
        "strict": _bool("SAML_STRICT", default=True),
        "debug": _bool("SAML_DEBUG", default=False),
        "sp": {
            "entityId": _value("SAML_SP_ENTITY_ID"),
            "assertionConsumerService": {
                "url": _value("SAML_SP_ACS_URL"),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "singleLogoutService": {
                "url": _value("SAML_SP_SLS_URL"),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "NameIDFormat": _value(
                "SAML_NAMEID_FORMAT",
                default="urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
            ),
        },
        "idp": {
            "entityId": _value("SAML_IDP_ENTITY_ID"),
            "singleSignOnService": {
                "url": _value("SAML_IDP_SSO_URL"),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "singleLogoutService": {
                "url": _value("SAML_IDP_SLO_URL"),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": _value("SAML_IDP_CERT"),
        },
        "security": {
            "authnRequestsSigned": _bool("SAML_SIGN_AUTHN_REQUESTS"),
            "logoutRequestSigned": _bool("SAML_SIGN_LOGOUT_REQUESTS"),
            "logoutResponseSigned": _bool("SAML_SIGN_LOGOUT_RESPONSES"),
            "wantMessagesSigned": _bool("SAML_WANT_MESSAGE_SIGNED"),
            "wantAssertionsSigned": _bool("SAML_WANT_ASSERTION_SIGNED", default=True),
            "wantNameId": True,
            "wantAttributeStatement": True,
            "requestedAuthnContext": requested_authn_context,
            "requestedAuthnContextComparison": requested_authn_context_comparison,
        },
    }

    if sp_cert:
        saml_config["sp"]["x509cert"] = sp_cert
    if sp_key:
        saml_config["sp"]["privateKey"] = sp_key

    multi_cert_raw = _value("SAML_IDP_CERT_MULTI")
    if multi_cert_raw:
        normalized = multi_cert_raw.replace("\\n", "\n")
        parts = normalized.replace(",", "\n").splitlines()
        certs = [part.strip() for part in parts if part.strip()]
        if certs:
            saml_config.setdefault("idp", {})["x509certMulti"] = {"signing": certs}
            saml_config["idp"].pop("x509cert", None)
    elif not saml_config["idp"].get("x509cert"):
        saml_config["idp"].pop("x509cert", None)

    allowed_groups = _list(_value("SAML_ALLOWED_GROUP_IDS"))

    return SamlSettings(
        config=saml_config,
        allowed_group_ids=allowed_groups,
        group_attribute=_value(
            "SAML_ATTRIBUTE_GROUPS",
            default="http://schemas.microsoft.com/identity/claims/groups",
        ),
        email_attribute=_value(
            "SAML_ATTRIBUTE_EMAIL",
            default="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        ),
        first_name_attribute=_value(
            "SAML_ATTRIBUTE_FIRST_NAME",
            default="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
        ),
        last_name_attribute=_value(
            "SAML_ATTRIBUTE_LAST_NAME",
            default="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
        ),
        display_name_attribute=_value(
            "SAML_ATTRIBUTE_DISPLAY_NAME",
            default="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
        ),
        object_id_attribute=_value(
            "SAML_ATTRIBUTE_OBJECT_ID",
            default="http://schemas.microsoft.com/identity/claims/objectidentifier",
        ),
        upn_attribute=_value(
            "SAML_ATTRIBUTE_UPN",
            default="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn",
        ),
        requested_authn_context=requested_authn_context,
        requested_authn_context_comparison=requested_authn_context_comparison,
    )


def prepare_request(flask_request) -> Dict[str, Any]:
    """Translate the current Flask request for python3-saml."""

    def _first_header(name: str) -> str | None:
        raw = flask_request.headers.get(name)
        if not raw:
            return None
        return raw.split(",", 1)[0].strip()

    url_scheme = (_first_header("X-Forwarded-Proto") or flask_request.scheme or "").lower()
    host = _first_header("X-Forwarded-Host") or flask_request.host
    port = _first_header("X-Forwarded-Port") or flask_request.environ.get("SERVER_PORT")
    prefix = _first_header("X-Forwarded-Prefix") or ""
    script_name = f"{prefix.rstrip('/')}{flask_request.path}" if prefix else flask_request.path

    if url_scheme == "https" and host and host.endswith(":443"):
        host = host.rsplit(":", 1)[0]
    if url_scheme == "http" and host and host.endswith(":80"):
        host = host.rsplit(":", 1)[0]

    return {
        "https": "on" if url_scheme == "https" else "off",
        "http_host": host,
        "server_port": port,
        "script_name": script_name,
        "query_string": flask_request.query_string.decode("utf-8"),
        "get_data": flask_request.args.copy(),
        "post_data": flask_request.form.copy(),
    }


def init_saml_auth(req_data: Mapping[str, Any], settings: SamlSettings) -> OneLogin_Saml2_Auth:
    return OneLogin_Saml2_Auth(req_data, old_settings=settings.config)


def attribute_first(attributes: Mapping[str, Iterable[str]], key: str) -> str:
    values = attributes.get(key)
    if not values:
        return ""
    for value in values:
        if value:
            return str(value).strip()
    return ""


def metadata_response(settings: SamlSettings):
    metadata = settings.sp_metadata()
    return metadata, "application/samlmetadata+xml"


def log_saml_error(message: str, errors: Iterable[str], reason: str | None = None) -> None:
    joined = ", ".join(errors)
    if reason:
        current_app.logger.error("%s: %s | reason=%s", message, joined if joined else "(no details)", reason)
    else:
        current_app.logger.error("%s: %s", message, joined if joined else "(no details)")


def _parse_requested_authn_context(raw: str) -> list[str] | bool:
    if not raw:
        return ["urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport"]

    lowered = raw.strip().lower()
    if lowered in {"none", "false", "off"}:
        return False

    values = [item.strip() for item in raw.split(",") if item.strip()]
    return values or ["urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport"]