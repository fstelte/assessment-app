"""Command-line helpers for the scaffold application."""

from __future__ import annotations

import click

from . import create_app


@click.group()
def main() -> None:
    """Scaffold management commands."""


@main.command()
def list_apps() -> None:
    """List registered application modules."""

    app = create_app()
    registry = app.extensions.get("scaffold_registry")
    if registry is None:
        click.echo("No registry found.")
        return

    for entry in registry.modules:
        click.echo(entry.name)
