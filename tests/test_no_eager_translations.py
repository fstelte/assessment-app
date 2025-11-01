import re
from pathlib import Path


EAGER_PATTERN = re.compile(r"cast\(str,\s*_l\(|cast\(str,\s*lazy_gettext\(|cast\(str,\s*_l\(")


def test_no_eager_lazy_translations():
    """Fail if code eagerly casts lazy translations to str at import time."""
    repo_root = Path(__file__).resolve().parents[1]
    matches = []
    for p in repo_root.rglob("*.py"):
        # skip virtualenvs or generated files (narrow by repo)
        if "/.venv/" in str(p) or "/.eggs/" in str(p):
            continue
        text = p.read_text(encoding="utf-8")
        if EAGER_PATTERN.search(text):
            matches.append(str(p))

    assert not matches, (
        "Found eager translation casts in files (use lazy_gettext and avoid cast(str, _l(...))):\n"
        + "\n".join(matches)
    )
