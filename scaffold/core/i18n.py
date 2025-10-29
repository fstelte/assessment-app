"""Lightweight JSON-backed internationalisation helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from flask import current_app, g


class TranslationError(RuntimeError):
    """Raised when a translation cannot be interpolated with provided variables."""


@dataclass(slots=True)
class TranslationManager:
    """Load and resolve translations stored as JSON files per locale."""

    translations_path: Path
    default_locale: str = "en"
    _catalog_by_locale: dict[str, dict[str, Any]] = field(init=False, default_factory=dict)
    _supported_locales: set[str] = field(init=False, default_factory=set)

    def __post_init__(self) -> None:
        self.translations_path = Path(self.translations_path)
        self.reload()

    def reload(self) -> None:
        """Re-read translation files from disk."""

        self._catalog_by_locale.clear()
        self._supported_locales.clear()
        if not self.translations_path.exists():
            return
        for path in sorted(self.translations_path.glob("*.json")):
            locale = path.stem
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            self._catalog_by_locale[locale] = data
            self._supported_locales.add(locale)
        if self.default_locale not in self._supported_locales:
            self._supported_locales.add(self.default_locale)
            self._catalog_by_locale.setdefault(self.default_locale, {})

    def available_locales(self) -> list[str]:
        return sorted(self._supported_locales)

    def translate(self, key: str, *, locale: str | None = None, **variables: Any) -> str:
        """Return the translation for *key* in *locale* formatting *variables*."""

        locale_to_use = locale if locale in self._supported_locales else self.default_locale
        message = self._lookup(locale_to_use, key)
        if message is None and locale_to_use != self.default_locale:
            message = self._lookup(self.default_locale, key)
        if message is None:
            message = key
        if variables:
            try:
                message = message.format(**variables)
            except KeyError as exc:  # pragma: no cover - defensive
                missing = exc.args[0]
                raise TranslationError(f"Missing placeholder '{missing}' for key '{key}'") from exc
        return message

    def _lookup(self, locale: str, key: str) -> str | None:
        data = self._catalog_by_locale.get(locale)
        if not isinstance(data, dict):
            return None
        return _resolve_nested_key(data, key)


def _resolve_nested_key(node: dict[str, Any], key: str) -> str | None:
    current: Any = node
    for part in key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current if isinstance(current, str) else None


_SESSION_KEY = "preferred_locale"


def get_locale() -> str:
    """Return the active locale for the current request."""

    manager = current_app.extensions.get("i18n")
    if not manager:
        return "en"
    locale = getattr(g, "active_locale", None)
    if locale and locale in manager.available_locales():
        return locale
    return manager.default_locale


def set_locale(locale: str) -> None:
    """Persist the active locale for the current request."""

    manager = current_app.extensions.get("i18n")
    if not manager:
        return
    if locale not in manager.available_locales():
        locale = manager.default_locale
    g.active_locale = locale


@lru_cache(maxsize=None)
def _fallback_translator(locale: str) -> TranslationManager:
    # Only used when app context is missing; ensures graceful degradation during CLI usage.
    dummy_path = (Path(__file__).resolve().parent.parent / "translations").resolve()
    return TranslationManager(dummy_path, default_locale=locale)


def gettext(key: str, **variables: Any) -> str:
    """Convenience wrapper usable from Python modules."""

    if current_app:
        manager: TranslationManager | None = current_app.extensions.get("i18n")
        if manager:
            return manager.translate(key, locale=get_locale(), **variables)
    fallback = _fallback_translator("en")
    return fallback.translate(key, **variables)


def session_storage_key() -> str:
    return _SESSION_KEY