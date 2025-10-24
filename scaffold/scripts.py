"""Utility commands exposed as Poetry scripts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run(command: list[str]) -> None:
    """Execute a command in the project root and mirror its exit code."""

    process = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if process.returncode != 0:
        raise SystemExit(process.returncode)


def lint() -> None:
    """Run static analysis tools."""

    _run([sys.executable, "-m", "ruff", "check", "."])
    _run([sys.executable, "-m", "black", "--check", "."])


def test() -> None:
    """Execute the test suite."""

    _run([sys.executable, "-m", "pytest"])


def run() -> None:
    """Start the development server."""

    from scaffold import create_app

    app = create_app()
    host = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "1") not in {"0", "false", "False"}
    app.run(host=host, port=port, debug=debug)
