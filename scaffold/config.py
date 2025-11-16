"""Application settings and environment helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

_DEFAULT_MODULES = [
    "scaffold.apps.auth.routes",
    "scaffold.apps.admin",
    "scaffold.apps.bia",
    "scaffold.apps.csa",
    "scaffold.apps.dpia",
    "scaffold.apps.pages",
    "scaffold.apps.template",
]


@dataclass(slots=True)
class Settings:
    """Simple settings container fed by environment variables."""

    secret_key: str = "change-me"
    database_url: str = "sqlite:///instance/scaffold.db"
    session_cookie_secure: bool = True
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "Lax"
    app_modules: List[str] = field(default_factory=lambda: list(_DEFAULT_MODULES))
    password_login_enabled: bool = False
    bia_components_per_page: int = 25
    saml_logout_return_url: str = ""
    saml_sp_entity_id: str = ""
    saml_sp_acs_url: str = ""
    saml_sp_sls_url: str = ""
    saml_sp_cert: str = ""
    saml_sp_private_key: str = ""
    saml_idp_entity_id: str = ""
    saml_idp_sso_url: str = ""
    saml_idp_slo_url: str = ""
    saml_idp_cert: str = ""
    saml_nameid_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"
    saml_sign_authn_requests: bool = False
    saml_sign_logout_requests: bool = False
    saml_sign_logout_responses: bool = False
    saml_want_message_signed: bool = False
    saml_want_assertion_signed: bool = True
    saml_allowed_group_ids: str = ""
    saml_role_map: str = ""
    saml_attribute_groups: str = "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups"
    saml_attribute_email: str = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
    saml_attribute_first_name: str = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname"
    saml_attribute_last_name: str = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname"
    saml_attribute_display_name: str = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"
    saml_attribute_object_id: str = "http://schemas.microsoft.com/identity/claims/objectidentifier"
    saml_attribute_upn: str = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn"
    saml_strict: bool = True
    saml_debug: bool = False
    saml_requested_authn_context: str = ""
    saml_requested_authn_context_comparison: str = "minimum"
    proxy_fix_enabled: bool = False
    proxy_fix_x_for: int = 1
    proxy_fix_x_proto: int = 1
    proxy_fix_x_host: int = 1
    proxy_fix_x_port: int = 0
    proxy_fix_x_prefix: int = 0
    preferred_url_scheme: str = "http"
    export_cleanup_enabled: bool = False
    export_cleanup_max_age_days: int = 7
    export_cleanup_interval_minutes: int = 60

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        modules = os.getenv("SCAFFOLD_APP_MODULES") or ""
        module_list = [m.strip() for m in modules.split(",") if m.strip()] or list(_DEFAULT_MODULES)
        return cls(
            secret_key=os.getenv("SECRET_KEY", defaults.secret_key),
            database_url=os.getenv("DATABASE_URL", defaults.database_url),
            session_cookie_secure=_as_bool(os.getenv("SESSION_COOKIE_SECURE", "true")),
            session_cookie_httponly=_as_bool(os.getenv("SESSION_COOKIE_HTTPONLY", "true")),
            session_cookie_samesite=os.getenv("SESSION_COOKIE_SAMESITE", defaults.session_cookie_samesite),
            app_modules=module_list,
            password_login_enabled=_resolve_password_login_enabled(defaults.password_login_enabled),
            bia_components_per_page=_int_env("BIA_COMPONENTS_PER_PAGE", defaults.bia_components_per_page),
            saml_logout_return_url=os.getenv("SAML_LOGOUT_RETURN_URL", defaults.saml_logout_return_url),
            saml_sp_entity_id=os.getenv("SAML_SP_ENTITY_ID", defaults.saml_sp_entity_id),
            saml_sp_acs_url=os.getenv("SAML_SP_ACS_URL", defaults.saml_sp_acs_url),
            saml_sp_sls_url=os.getenv("SAML_SP_SLS_URL", defaults.saml_sp_sls_url),
            saml_sp_cert=os.getenv("SAML_SP_CERT", defaults.saml_sp_cert),
            saml_sp_private_key=os.getenv("SAML_SP_PRIVATE_KEY", defaults.saml_sp_private_key),
            saml_idp_entity_id=os.getenv("SAML_IDP_ENTITY_ID", defaults.saml_idp_entity_id),
            saml_idp_sso_url=os.getenv("SAML_IDP_SSO_URL", defaults.saml_idp_sso_url),
            saml_idp_slo_url=os.getenv("SAML_IDP_SLO_URL", defaults.saml_idp_slo_url),
            saml_idp_cert=os.getenv("SAML_IDP_CERT", defaults.saml_idp_cert),
            saml_nameid_format=os.getenv("SAML_NAMEID_FORMAT", defaults.saml_nameid_format),
            saml_sign_authn_requests=_bool_env("SAML_SIGN_AUTHN_REQUESTS", defaults.saml_sign_authn_requests),
            saml_sign_logout_requests=_bool_env("SAML_SIGN_LOGOUT_REQUESTS", defaults.saml_sign_logout_requests),
            saml_sign_logout_responses=_bool_env("SAML_SIGN_LOGOUT_RESPONSES", defaults.saml_sign_logout_responses),
            saml_want_message_signed=_bool_env("SAML_WANT_MESSAGE_SIGNED", defaults.saml_want_message_signed),
            saml_want_assertion_signed=_as_bool(os.getenv("SAML_WANT_ASSERTION_SIGNED", "true")),
            saml_allowed_group_ids=os.getenv("SAML_ALLOWED_GROUP_IDS", defaults.saml_allowed_group_ids),
            saml_role_map=os.getenv("SAML_ROLE_MAP", defaults.saml_role_map),
            saml_attribute_groups=os.getenv("SAML_ATTRIBUTE_GROUPS", defaults.saml_attribute_groups),
            saml_attribute_email=os.getenv("SAML_ATTRIBUTE_EMAIL", defaults.saml_attribute_email),
            saml_attribute_first_name=os.getenv("SAML_ATTRIBUTE_FIRST_NAME", defaults.saml_attribute_first_name),
            saml_attribute_last_name=os.getenv("SAML_ATTRIBUTE_LAST_NAME", defaults.saml_attribute_last_name),
            saml_attribute_display_name=os.getenv("SAML_ATTRIBUTE_DISPLAY_NAME", defaults.saml_attribute_display_name),
            saml_attribute_object_id=os.getenv("SAML_ATTRIBUTE_OBJECT_ID", defaults.saml_attribute_object_id),
            saml_attribute_upn=os.getenv("SAML_ATTRIBUTE_UPN", defaults.saml_attribute_upn),
            saml_strict=_as_bool(os.getenv("SAML_STRICT", "true")),
            saml_debug=_as_bool(os.getenv("SAML_DEBUG")),
            saml_requested_authn_context=os.getenv("SAML_REQUESTED_AUTHN_CONTEXT", defaults.saml_requested_authn_context),
            saml_requested_authn_context_comparison=os.getenv(
                "SAML_REQUESTED_AUTHN_CONTEXT_COMPARISON",
                defaults.saml_requested_authn_context_comparison,
            ),
            proxy_fix_enabled=_as_bool(os.getenv("PROXY_FIX_ENABLED")),
            proxy_fix_x_for=_int_env("PROXY_FIX_X_FOR", defaults.proxy_fix_x_for),
            proxy_fix_x_proto=_int_env("PROXY_FIX_X_PROTO", defaults.proxy_fix_x_proto),
            proxy_fix_x_host=_int_env("PROXY_FIX_X_HOST", defaults.proxy_fix_x_host),
            proxy_fix_x_port=_int_env("PROXY_FIX_X_PORT", defaults.proxy_fix_x_port),
            proxy_fix_x_prefix=_int_env("PROXY_FIX_X_PREFIX", defaults.proxy_fix_x_prefix),
            preferred_url_scheme=os.getenv("PREFERRED_URL_SCHEME", defaults.preferred_url_scheme),
            export_cleanup_enabled=_as_bool(os.getenv("EXPORT_CLEANUP_ENABLED")) or defaults.export_cleanup_enabled,
            export_cleanup_max_age_days=_int_env("EXPORT_CLEANUP_MAX_AGE_DAYS", defaults.export_cleanup_max_age_days),
            export_cleanup_interval_minutes=_int_env("EXPORT_CLEANUP_INTERVAL_MINUTES", defaults.export_cleanup_interval_minutes),
        )

    def flask_config(self) -> dict[str, object]:
        """Return the Flask configuration dictionary."""

        return {
            "SECRET_KEY": self.secret_key,
            "SQLALCHEMY_DATABASE_URI": self.database_url,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SESSION_COOKIE_SECURE": self.session_cookie_secure,
            "SESSION_COOKIE_HTTPONLY": self.session_cookie_httponly,
            "SESSION_COOKIE_SAMESITE": self.session_cookie_samesite,
            "PASSWORD_LOGIN_ENABLED": self.password_login_enabled,
            "BIA_COMPONENTS_PER_PAGE": self.bia_components_per_page,
            "SAML_LOGOUT_RETURN_URL": self.saml_logout_return_url,
            "SAML_SP_ENTITY_ID": self.saml_sp_entity_id,
            "SAML_SP_ACS_URL": self.saml_sp_acs_url,
            "SAML_SP_SLS_URL": self.saml_sp_sls_url,
            "SAML_SP_CERT": self.saml_sp_cert,
            "SAML_SP_PRIVATE_KEY": self.saml_sp_private_key,
            "SAML_IDP_ENTITY_ID": self.saml_idp_entity_id,
            "SAML_IDP_SSO_URL": self.saml_idp_sso_url,
            "SAML_IDP_SLO_URL": self.saml_idp_slo_url,
            "SAML_IDP_CERT": self.saml_idp_cert,
            "SAML_NAMEID_FORMAT": self.saml_nameid_format,
            "SAML_SIGN_AUTHN_REQUESTS": self.saml_sign_authn_requests,
            "SAML_SIGN_LOGOUT_REQUESTS": self.saml_sign_logout_requests,
            "SAML_SIGN_LOGOUT_RESPONSES": self.saml_sign_logout_responses,
            "SAML_WANT_MESSAGE_SIGNED": self.saml_want_message_signed,
            "SAML_WANT_ASSERTION_SIGNED": self.saml_want_assertion_signed,
            "SAML_ALLOWED_GROUP_IDS": self.saml_allowed_group_ids,
            "SAML_ALLOWED_GROUP_IDS_LIST": self.saml_allowed_groups(),
            "SAML_ROLE_MAP": self.saml_role_map,
            "SAML_ATTRIBUTE_GROUPS": self.saml_attribute_groups,
            "SAML_ATTRIBUTE_EMAIL": self.saml_attribute_email,
            "SAML_ATTRIBUTE_FIRST_NAME": self.saml_attribute_first_name,
            "SAML_ATTRIBUTE_LAST_NAME": self.saml_attribute_last_name,
            "SAML_ATTRIBUTE_DISPLAY_NAME": self.saml_attribute_display_name,
            "SAML_ATTRIBUTE_OBJECT_ID": self.saml_attribute_object_id,
            "SAML_ATTRIBUTE_UPN": self.saml_attribute_upn,
            "SAML_STRICT": self.saml_strict,
            "SAML_DEBUG": self.saml_debug,
            "SAML_REQUESTED_AUTHN_CONTEXT": self.saml_requested_authn_context,
            "SAML_REQUESTED_AUTHN_CONTEXT_COMPARISON": self.saml_requested_authn_context_comparison,
            "PROXY_FIX_ENABLED": self.proxy_fix_enabled,
            "PROXY_FIX_X_FOR": self.proxy_fix_x_for,
            "PROXY_FIX_X_PROTO": self.proxy_fix_x_proto,
            "PROXY_FIX_X_HOST": self.proxy_fix_x_host,
            "PROXY_FIX_X_PORT": self.proxy_fix_x_port,
            "PROXY_FIX_X_PREFIX": self.proxy_fix_x_prefix,
            "PREFERRED_URL_SCHEME": self.preferred_url_scheme,
            "EXPORT_CLEANUP_ENABLED": self.export_cleanup_enabled,
            "EXPORT_CLEANUP_MAX_AGE_DAYS": self.export_cleanup_max_age_days,
            "EXPORT_CLEANUP_INTERVAL_MINUTES": self.export_cleanup_interval_minutes,
        }

    def saml_allowed_groups(self) -> List[str]:
        """Return SAML group identifiers as a trimmed list."""

        return [gid.strip() for gid in self.saml_allowed_group_ids.split(",") if gid.strip()]


def _as_bool(raw: str | None) -> bool:
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _bool_env(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return _as_bool(raw)


def _int_env(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _resolve_password_login_enabled(default: bool) -> bool:
    for key in (
        "PASSWORD_LOGIN_ENABLED",
        "SAML_PASSWORD_LOGIN_ENABLED",
        "ENTRA_PASSWORD_LOGIN_ENABLED",
        "AZURE_PASSWORD_LOGIN_ENABLED",
    ):
        raw = os.getenv(key)
        if raw is not None:
            return _as_bool(raw)
    return default
