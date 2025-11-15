"""Compatibility module retained for backward imports.

The application now uses SAML exclusively and no longer exposes Microsoft Entra
OIDC helpers. Importing this module indicates stale code paths.
"""

from __future__ import annotations


def __getattr__(name: str):  # pragma: no cover - defensive guard for legacy imports
    raise RuntimeError(
        "scaffold.apps.auth.entra has been removed; migrate to the SAML helper "
        "(scaffold.apps.auth.saml) and update configuration to use SAML_* settings."
    )
