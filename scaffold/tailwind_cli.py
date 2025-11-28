"""Lightweight Tailwind CSS launcher managed through Poetry.

This module downloads the official Tailwind standalone binary for the current
platform (macOS, Linux, or Windows) and caches it under ``.tailwind/`` inside
this repository. The helper is exposed as the ``tailwind`` Poetry script so you
can run ``poetry run tailwind <args>`` without installing Node.js globally.
"""

from __future__ import annotations

import os
import platform
import shutil
import stat
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / ".tailwind"
DEFAULT_VERSION = "3.4.10"


class TailwindCLIError(RuntimeError):
    """Raised when the Tailwind CLI binary cannot be prepared."""


def _requested_version() -> str:
    return (
        os.environ.get("TAILWINDCSS_VERSION")
        or os.environ.get("TAILWIND_VERSION")
        or DEFAULT_VERSION
    )


def _platform_asset() -> tuple[str, str]:
    """Return the release asset name and desired filename for this platform."""

    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        arch = "arm64" if "arm" in machine or "aarch64" in machine else "x64"
        return f"tailwindcss-macos-{arch}", "tailwindcss"

    if system == "linux":
        arch = "arm64" if "aarch64" in machine or "arm" in machine else "x64"
        return f"tailwindcss-linux-{arch}", "tailwindcss"

    if system == "windows":
        # Tailwind only ships a 64-bit Windows build.
        return "tailwindcss-windows-x64.exe", "tailwindcss.exe"

    raise TailwindCLIError(f"Unsupported platform: {system} {machine}")


def _binary_path(version: str, filename: str) -> Path:
    binary_dir = CACHE_DIR / version
    binary_dir.mkdir(parents=True, exist_ok=True)
    return binary_dir / filename


def _download_binary(version: str) -> Path:
    asset_name, filename = _platform_asset()
    target_path = _binary_path(version, filename)
    if target_path.exists():
        return target_path

    asset_url = (
        f"https://github.com/tailwindlabs/tailwindcss/releases/download/v{version}/{asset_name}"
    )
    temp_path = target_path.with_suffix(target_path.suffix + ".download")

    try:
        with urllib.request.urlopen(asset_url) as response, open(temp_path, "wb") as handle:
            shutil.copyfileobj(response, handle)
    except urllib.error.URLError as exc:  # pragma: no cover - network failure path
        raise TailwindCLIError(
            f"Unable to download Tailwind CLI v{version} from {asset_url}: {exc}"
        ) from exc

    temp_path.chmod(temp_path.stat().st_mode | stat.S_IEXEC)
    temp_path.rename(target_path)
    return target_path


def _ensure_binary(version: str) -> Path:
    _, filename = _platform_asset()
    target_path = _binary_path(version, filename)
    if target_path.exists():
        return target_path

    # Download if not cached yet.
    return _download_binary(version)


def cli() -> None:
    """Entry point used by Poetry to run Tailwind."""

    args = sys.argv[1:]
    version = _requested_version()

    try:
        binary = _ensure_binary(version)
    except TailwindCLIError as exc:
        sys.stderr.write(f"Tailwind CLI error: {exc}\n")
        raise SystemExit(1) from exc

    process = subprocess.run([str(binary), *args], check=False)
    raise SystemExit(process.returncode)


if __name__ == "__main__":  # pragma: no cover - manual execution convenience
    cli()
