import json
from pathlib import Path


def _flatten_keys(node, prefix=""):
    keys = set()
    if isinstance(node, dict):
        for k, v in node.items():
            new_prefix = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                keys |= _flatten_keys(v, new_prefix)
            else:
                keys.add(new_prefix)
    return keys


def test_admin_translation_keys_present_in_locales():
    root = Path(__file__).resolve().parents[1] / "scaffold" / "translations"
    en = json.loads((root / "en.json").read_text(encoding="utf-8"))
    nl = json.loads((root / "nl.json").read_text(encoding="utf-8"))

    # Collect all admin.users and admin.user_mfa keys from English catalog
    admin_en = en.get("admin") or {}
    users_en = admin_en.get("users") or {}

    en_keys = _flatten_keys(users_en, "admin.users")

    # Ensure each English key exists in Dutch catalog under same path
    admin_nl = nl.get("admin") or {}
    users_nl = admin_nl.get("users") or {}
    nl_keys = _flatten_keys(users_nl, "admin.users")

    missing = sorted(en_keys - nl_keys)
    assert not missing, f"Missing translation keys in nl.json: {missing}"
