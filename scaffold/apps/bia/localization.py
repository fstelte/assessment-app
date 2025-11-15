"""Locale-aware helpers for BIA authentication method labels."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Mapping

from flask import current_app

from ...core.i18n import TranslationManager

_TRANSLATION_NAMESPACE = "bia.authentication_methods.options"


@lru_cache(maxsize=1)
def _fallback_manager() -> TranslationManager:
    """Return a translation manager for use outside application contexts."""

    translations_dir = Path(__file__).resolve().parents[2] / "translations"
    return TranslationManager(translations_dir)


def translate_authentication_label(
    slug: str,
    locale: str | None = None,
    fallbacks: Mapping[str, str] | None = None,
) -> str:
    """Resolve the display label for *slug* in *locale*.

    When the requested translation is missing the function falls back to provided
    *fallbacks* and finally to a prettified slug.
    """

    key = f"{_TRANSLATION_NAMESPACE}.{slug}"
    manager: TranslationManager | None = None
    if current_app:
        manager = current_app.extensions.get("i18n")  # type: ignore[assignment]
    default_locale = "en"
    if manager is not None:
        default_locale = manager.default_locale
        message = manager.translate(key, locale=locale)
    else:
        fallback_manager = _fallback_manager()
        default_locale = fallback_manager.default_locale
        message = fallback_manager.translate(key, locale=locale)
    if message == key or not message:
        message = None

    if message:
        return message

    fallback_labels = fallbacks or {}
    requested = (locale or "").strip().lower()
    requested_short = requested.split("-")[0] if requested else ""

    seen: set[str] = set()
    candidates = [candidate for candidate in (requested, requested_short, default_locale) if candidate]
    candidates.extend(fallback_labels.keys())

    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        label = fallback_labels.get(candidate)
        if label:
            return label

    for label in fallback_labels.values():
        if label:
            return label

    return slug.replace("-", " ").title()
