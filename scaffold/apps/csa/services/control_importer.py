"""Import controls and assessment templates from structured data."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from sqlalchemy import or_, select

from ....extensions import db
from ..models import AssessmentTemplate, Control


CODE_PREFIX_PATTERN = re.compile(r"^\s*(?P<code>\d+(?:\.\d+)*[A-Za-z0-9]*)")
CODE_SUFFIX_PATTERN = re.compile(r"(?P<code>\d+(?:\.\d+)*[A-Za-z0-9]*)\s*$")
NAME_SPLIT_PATTERN = re.compile(r"\s*[-–—]\s*")

PROJECT_ROOT = Path(__file__).resolve().parents[4]
BUILTIN_CONTROL_DATASETS = {
    "iso": PROJECT_ROOT / "iso_27002_controls.json",
    "nist": PROJECT_ROOT / "nist_sp_800-53r5_controls.json",
}


@dataclass(frozen=True)
class ControlMetadata:
    """Normalised representation of incoming control data."""

    domain: str
    section: str | None
    description: str | None
    label: str
    code: str | None
    category: str | None
    search_keys: tuple[str, ...]


@dataclass
class ImportStats:
    """Capture import outcomes for reporting in the UI."""

    created: int = 0
    updated: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class UpsertOutcome:
    """Describe the outcome of inserting or updating a control entry."""

    control: Control
    created: bool
    updated_count: int


def _split_name_and_description(name: str, description: str | None) -> tuple[str, str | None]:
    """Split combined name/description strings when description is missing."""

    if description:
        return name, description

    parts = NAME_SPLIT_PATTERN.split(name, maxsplit=1)
    if len(parts) == 2:
        candidate_name, candidate_description = parts[0].strip(), parts[1].strip()
        if candidate_description:
            return candidate_name or name, candidate_description

    return name, description


def _normalise_control_metadata(entry: Mapping[str, Any]) -> ControlMetadata:
    raw_name = str(entry.get("name") or "").strip()
    section_text = str(entry.get("section") or "").strip()
    raw_id = str(entry.get("id") or "").strip()
    clause = str(entry.get("clause") or "").strip() or None
    description = (entry.get("description") or "").strip() or None
    category = str(entry.get("domain") or "").strip() or None

    if not (raw_name or section_text):
        raise ValueError("Control entry requires a 'name' or 'section' field")

    label_source = raw_name or section_text

    code = None
    if raw_name:
        prefix_match = CODE_PREFIX_PATTERN.match(raw_name)
        if prefix_match:
            code = prefix_match.group("code")

    if not code and raw_id:
        suffix_match = CODE_SUFFIX_PATTERN.search(raw_id)
        if suffix_match:
            code = suffix_match.group("code")

    if not code and section_text:
        prefix_match = CODE_PREFIX_PATTERN.match(section_text)
        if prefix_match:
            code = prefix_match.group("code")

    if not code and clause:
        code = clause

    label_source_clean = label_source
    if code and label_source.startswith(code):
        label_source_clean = label_source[len(code) :].strip(" .-–—")

    label, description = _split_name_and_description(label_source_clean or label_source, description)
    section = code or clause or None
    domain = label or label_source or raw_id or section_text

    combined_with_code = f"{code} {label}".strip() if code and label else None

    search_candidates: dict[str, None] = {}
    for candidate in (
        raw_name,
        section_text,
        raw_id,
        label,
        code,
        clause if clause and clause != code else None,
        category,
        combined_with_code if combined_with_code and combined_with_code != raw_name else None,
        f"{label} - {description}" if description else None,
    ):
        if candidate:
            search_candidates[candidate] = None

    return ControlMetadata(
        domain=domain,
        section=section,
        description=description,
        label=label,
        code=code,
        category=category,
        search_keys=tuple(search_candidates.keys()),
    )


def _build_payload(source: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    controls = source.get("controls")
    if not isinstance(controls, list):
        raise ValueError("Payload must include a 'controls' list")
    return controls


def _match_controls(metadata: ControlMetadata) -> list[Control]:
    domain_candidates = [candidate for candidate in (metadata.domain, *metadata.search_keys) if candidate]

    match_filters: list[Any] = []
    if domain_candidates:
        match_filters.append(Control.domain.in_(domain_candidates))
        match_filters.append(Control.section.in_(domain_candidates))
    if metadata.description:
        match_filters.append(Control.description == metadata.description)

    if not match_filters:
        return []

    condition = match_filters[0] if len(match_filters) == 1 else or_(*match_filters)
    return list(db.session.execute(select(Control).where(condition)).scalars())


def _create_control_with_template(metadata: ControlMetadata) -> Control:
    control = Control()
    control.section = metadata.section or metadata.domain
    control.domain = metadata.domain
    control.description = metadata.description
    db.session.add(control)
    db.session.flush()

    template = AssessmentTemplate()
    template.control = control
    template.name = (
        " ".join(part for part in (metadata.section, metadata.domain) if part).strip()
        or metadata.domain
    )
    template.version = "1.0"
    template.question_set = AssessmentTemplate.default_question_set()
    db.session.add(template)
    return control


def build_control_metadata(
    *,
    name: str,
    section: str | None = None,
    description: str | None = None,
    code: str | None = None,
    category: str | None = None,
) -> ControlMetadata:
    payload: dict[str, Any] = {"name": name}
    if section:
        payload["section"] = section
    if description:
        payload["description"] = description
    if code:
        payload["clause"] = code
    if category:
        payload["domain"] = category
    return _normalise_control_metadata(payload)


def upsert_control(
    metadata: ControlMetadata,
    *,
    allow_existing: bool = True,
    target: Control | None = None,
) -> UpsertOutcome:
    if target is not None:
        matching_controls = [target]
    else:
        matching_controls = _match_controls(metadata)

    if matching_controls and not allow_existing and target is None:
        raise ValueError("Control with the provided metadata already exists")

    if matching_controls:
        preferred_control = next(
            (item for item in matching_controls if item.domain == metadata.domain),
            matching_controls[0],
        )

        for item in matching_controls:
            item.description = metadata.description
            item.section = metadata.section or item.section
            if preferred_control is item:
                item.domain = metadata.domain

        return UpsertOutcome(control=preferred_control, created=False, updated_count=len(matching_controls))

    control = _create_control_with_template(metadata)
    return UpsertOutcome(control=control, created=True, updated_count=0)


def import_controls_from_mapping(payload: Mapping[str, Any]) -> ImportStats:
    """Import controls using a payload that contains a 'controls' array."""

    stats = ImportStats()
    controls = _build_payload(payload)

    for raw in controls:
        if not isinstance(raw, Mapping):
            stats.errors.append("Control entry is not a mapping; skipped")
            continue

        try:
            metadata = _normalise_control_metadata(raw)
        except ValueError as exc:
            stats.errors.append(str(exc))
            continue

        outcome = upsert_control(metadata)
        if outcome.created:
            stats.created += 1
        else:
            stats.updated += outcome.updated_count

    db.session.commit()
    return stats


def import_controls_from_file(path: Path | str) -> ImportStats:
    """Import controls from a JSON file path."""

    resolved = Path(path)
    with resolved.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return import_controls_from_mapping(payload)


def resolve_builtin_dataset(name: str) -> Path:
    """Resolve the on-disk path for a known builtin dataset."""

    try:
        path = BUILTIN_CONTROL_DATASETS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown builtin control dataset '{name}'.") from exc
    return path


def _parse_nist_lines(lines: Iterable[str]) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    description_lines: list[str] = []

    def flush_current() -> None:
        nonlocal current, description_lines
        if not current:
            return

        control_id = current.get("id")
        section = current.get("section")
        if not control_id:
            raise ValueError("Encountered a control without an identifier in the NIST dataset.")
        if not section:
            raise ValueError(f"Control '{control_id}' is missing a section title in the NIST dataset.")

        description = " ".join(part for part in (line.strip() for line in description_lines) if part) or None
        controls.append(
            {
                "id": control_id,
                "section": section,
                "name": section,
                "domain": current.get("domain"),
                "description": description,
            }
        )

        current = {}
        description_lines = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("framework "):
            continue

        if line.startswith("id "):
            flush_current()
            current = {"id": line[3:].strip()}
            description_lines = []
            continue

        if line.startswith("section "):
            current["section"] = line[len("section ") :].strip()
            continue

        if line.startswith("domain "):
            current["domain"] = line[len("domain ") :].strip()
            continue

        if line.startswith("baselines") or line.startswith("enhancements"):
            continue

        if line.startswith("-"):
            description_lines.append(line.lstrip("- ").strip())
            continue

        if description_lines:
            description_lines.append(line)

    flush_current()

    if not controls:
        raise ValueError("NIST dataset did not contain any controls.")

    return controls


def parse_nist_text(text: str) -> Mapping[str, Any]:
    """Parse an in-memory NIST control export string."""

    return {"controls": _parse_nist_lines(text.splitlines())}


def parse_nist_controls(path: Path | str) -> Mapping[str, Any]:
    """Parse the plain-text NIST control export into the canonical mapping format."""

    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"NIST dataset not found at {resolved}.")

    with resolved.open("r", encoding="utf-8") as handle:
        controls = _parse_nist_lines(handle)
    return {"controls": controls}


def import_controls_from_builtin(dataset: str) -> ImportStats:
    """Import one of the bundled control datasets by shorthand name."""

    resolved = resolve_builtin_dataset(dataset)
    if dataset == "nist":
        payload = parse_nist_controls(resolved)
        return import_controls_from_mapping(payload)

    return import_controls_from_file(resolved)
