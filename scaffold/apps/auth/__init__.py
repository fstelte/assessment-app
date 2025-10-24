"""Authentication module package."""

from __future__ import annotations

from ...templates.navigation import NavEntry

NAVIGATION = [
	NavEntry(endpoint="auth.login", label="Sign In", order=90),
]
