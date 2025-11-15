"""Helpers for working with BIA authentication method lookups."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from ....core.i18n import get_locale
from ..localization import translate_authentication_label
from ..models import AuthenticationMethod


@dataclass(frozen=True)
class AuthenticationOption:
    """Snapshot of an authentication method option."""

    id: int
    slug: str
    fallback_labels: dict[str, str]
    is_active: bool

    def label(self, locale: str | None = None) -> str:
        """Return the translated label for *locale*. Defaults to English."""

        return translate_authentication_label(self.slug, locale, self.fallback_labels)

    def label_for_locale(self, locale: str) -> str:
        """Return the translated label for the specific locale."""

        return translate_authentication_label(self.slug, locale, self.fallback_labels)


@lru_cache(maxsize=2)
def _load_options(active_only: bool) -> tuple[AuthenticationOption, ...]:
    query = AuthenticationMethod.query.order_by(AuthenticationMethod.slug.asc(), AuthenticationMethod.id.asc())
    if active_only:
        query = query.filter(AuthenticationMethod.is_active.is_(True))
    options = []
    for record in query:
        fallback_labels = {
            "en": record.label_en or "",
            "nl": record.label_nl or "",
        }
        options.append(
            AuthenticationOption(
                id=record.id,
                slug=record.slug,
                fallback_labels=fallback_labels,
                is_active=record.is_active,
            )
        )
    options.sort(key=lambda option: option.label_for_locale("en").lower())
    return tuple(options)


def clear_authentication_cache() -> None:
    """Invalidate cached authentication lookup data."""

    _load_options.cache_clear()


def list_authentication_options(*, active_only: bool = True) -> tuple[AuthenticationOption, ...]:
    """Return available authentication methods ordered by their English label."""

    return _load_options(active_only)


def form_choices(locale: str | None = None, *, include_inactive: bool = False) -> list[tuple[str, str]]:
    """Return WTForms-compatible choices for the current locale."""

    options = _load_options(not include_inactive)
    locale_to_use = locale or get_locale()
    return [(str(option.id), option.label(locale_to_use)) for option in options]


def lookup_by_id(identifier: int) -> AuthenticationOption | None:
    """Return option snapshot for *identifier* if present."""

    for option in _load_options(active_only=False):
        if option.id == identifier:
            return option
    return None


def lookup_by_slug(slug: str) -> AuthenticationOption | None:
    """Return option snapshot for *slug* if present."""

    slug_normalised = slug.strip().lower()
    if not slug_normalised:
        return None
    for option in _load_options(active_only=False):
        if option.slug.lower() == slug_normalised:
            return option
    return None


def ensure_seeded(slug: str, label_en: str, label_nl: str) -> AuthenticationMethod:
    """Create or refresh a method with the provided labels.

    This is primarily used from migrations or bootstrap scripts.
    """

    option = AuthenticationMethod.query.filter(AuthenticationMethod.slug == slug).first()
    if option is None:
        option = AuthenticationMethod(slug=slug)
    fallback = {"en": label_en, "nl": label_nl}
    option.label_en = translate_authentication_label(slug, "en", fallback)
    option.label_nl = translate_authentication_label(slug, "nl", fallback)
    option.is_active = True
    return option
