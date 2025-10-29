"""Template module showing how to extend the scaffold with new domains."""

from __future__ import annotations

from flask import Blueprint, render_template

from ...templates.navigation import NavEntry

blueprint = Blueprint("template", __name__, template_folder="templates")


@blueprint.get("/")
def index():
    return render_template("template/index.html")


def register(app):
    """Hook called by the app registry to bind the template blueprint."""

    app.register_blueprint(blueprint)
    app.logger.info("Template module registered; replace with custom domain logic.")


NAVIGATION = [
    NavEntry(endpoint="template.index", label="app.navigation.home", order=10),
]
