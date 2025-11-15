"""Deprecated Azure helper module.

The SAML-only authentication stack removed the legacy Azure/MSAL helpers. Any
remaining imports of this module should be migrated to
``scaffold.apps.auth.saml``.
"""

from __future__ import annotations


def __getattr__(name: str):  # pragma: no cover - defensive guard for legacy imports
    raise RuntimeError(
        "scaffold.apps.auth.azure has been removed; update integrations to rely "
        "on SAML-based configuration and helpers."
    )