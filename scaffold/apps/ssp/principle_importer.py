"""Import architecture principles from structured data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from sqlalchemy import func, select

from ...extensions import db
from .models import ArchitecturePrinciple


@dataclass
class ImportStats:
    """Capture import outcomes for reporting in the UI."""

    created: int = 0
    updated: int = 0
    errors: list[str] = field(default_factory=list)


def _normalise_name(name: str) -> str:
    return name.strip().casefold()


def _build_payload(source: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    principles = source.get("principles")
    if not isinstance(principles, list):
        raise ValueError("Payload must include a 'principles' list")
    return principles


def upsert_principle(name: str, description: str) -> tuple[ArchitecturePrinciple, bool]:
    """Create or update a principle by case-insensitive name match.

    Returns (principle, created).
    """

    existing = db.session.execute(
        select(ArchitecturePrinciple).where(func.lower(ArchitecturePrinciple.name) == _normalise_name(name))
    ).scalar_one_or_none()

    if existing is not None:
        existing.description = description
        return existing, False

    principle = ArchitecturePrinciple(name=name.strip(), description=description)
    db.session.add(principle)
    db.session.flush()
    return principle, True


def import_principles_from_mapping(payload: Mapping[str, Any]) -> ImportStats:
    """Import architecture principles using a payload with a 'principles' array."""

    stats = ImportStats()
    principles = _build_payload(payload)

    seen_at_row: dict[str, int] = {}
    for index, raw in enumerate(principles, start=1):
        if not isinstance(raw, Mapping):
            stats.errors.append(f"Entry {index} is not a mapping; skipped")
            continue

        name = str(raw.get("name") or "").strip()
        description = str(raw.get("description") or "").strip()
        if not name or not description:
            stats.errors.append(f"Entry {index} requires both 'name' and 'description'")
            continue

        normalised = _normalise_name(name)
        if normalised in seen_at_row:
            stats.errors.append(
                f"'{name}' (row {seen_at_row[normalised]}) was superseded within the file by row {index}"
            )
        seen_at_row[normalised] = index

        _, created = upsert_principle(name, description)
        if created:
            stats.created += 1
        else:
            stats.updated += 1

    db.session.commit()
    return stats
