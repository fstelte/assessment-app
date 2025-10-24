"""Navigation helpers for dynamically registered app sections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from flask import Flask, url_for


@dataclass(slots=True)
class NavEntry:
    endpoint: str
    label: str
    icon: str | None = None
    order: int = 100

    def resolve(self) -> dict[str, object]:
        return {
            "endpoint": self.endpoint,
            "label": self.label,
            "url": url_for(self.endpoint),
            "icon": self.icon,
            "order": self.order,
        }


def default_entries(app: Flask) -> List[NavEntry]:
    entries: List[NavEntry] = []
    registry = app.extensions.get("scaffold_registry")
    if registry:
        for record in registry.modules:
            nav_items = getattr(record.module, "NAVIGATION", None)
            if nav_items:
                entries.extend(nav_items)
    seen: set[str] = set()
    resolved: list[NavEntry] = []
    for entry in sorted(entries, key=lambda item: (item.order, item.label)):
        if entry.endpoint in seen:
            continue
        seen.add(entry.endpoint)
        resolved.append(entry)
    return resolved


def build_navigation(app: Flask) -> list[dict[str, object]]:
    return [entry.resolve() for entry in default_entries(app)]
