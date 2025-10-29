"""General content pages for the scaffold application."""

from __future__ import annotations

from typing import List

from flask import Blueprint, render_template

blueprint = Blueprint("pages", __name__, template_folder="templates")

CHANGELOG_ENTRIES: List[dict[str, object]] = [
    {
        "version": "2025.10.29",
        "date": "2025-10-29",
        "title_key": "pages.changelog.entries.20251029.title",
        "item_keys": [
            "pages.changelog.entries.20251029.items.locale_preference",
            "pages.changelog.entries.20251029.items.login_selector",
            "pages.changelog.entries.20251029.items.catalog_repair",
        ],
    },
    {
        "version": "2025.10.24",
        "date": "2025-10-24",
        "title_key": "pages.changelog.entries.20251024.title",
        "item_keys": [
            "pages.changelog.entries.20251024.items.foundation",
            "pages.changelog.entries.20251024.items.documentation",
        ],
    },
]


@blueprint.get("/changelog")
def changelog():
    """Render the project change log."""

    last_updated = CHANGELOG_ENTRIES[0]["date"] if CHANGELOG_ENTRIES else ""
    return render_template(
        "pages/changelog.html",
        entries=CHANGELOG_ENTRIES,
        last_updated=last_updated,
    )


def register(app):
    """Register the content blueprint with the application."""

    app.register_blueprint(blueprint)
