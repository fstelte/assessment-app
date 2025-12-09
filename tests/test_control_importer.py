from pathlib import Path

import pytest

from scaffold.apps.csa.services.control_importer import parse_nist_controls, parse_nist_text


def test_parse_nist_controls_parses_sample():
    sample_path = Path(__file__).with_name("data") / "nist_sample.txt"
    payload = parse_nist_controls(sample_path)

    controls = payload.get("controls")
    assert controls is not None
    assert len(controls) == 2

    first = controls[0]
    assert first["id"] == "NIST.SP.800-53r5 AC-1"
    assert first["section"] == "Policy and Procedures"
    assert "policy guidance" in (first.get("description") or "")
    assert first["domain"] == "AC Access Control"


def test_parse_nist_controls_requires_section(tmp_path):
    broken_path = tmp_path / "broken.txt"
    broken_path.write_text(
        """framework test
id NIST.SP.800-53r5 AC-X
- Missing section label
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        parse_nist_controls(broken_path)


def test_parse_nist_text_parses_in_memory_sample():
    sample_path = Path(__file__).with_name("data") / "nist_sample.txt"
    payload = parse_nist_text(sample_path.read_text(encoding="utf-8"))

    controls = payload.get("controls")
    assert controls is not None
    assert len(controls) == 2
    assert controls[1]["id"] == "NIST.SP.800-53r5 AT-2"
