"""Import controls and assessment templates from structured data."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from sqlalchemy import or_, select

from ..extensions import db
from ..models import AssessmentTemplate, Control


CODE_PREFIX_PATTERN = re.compile(r"^\s*(?P<code>\d+(?:\.\d+)*[A-Za-z0-9]*)")
CODE_SUFFIX_PATTERN = re.compile(r"(?P<code>\d+(?:\.\d+)*[A-Za-z0-9]*)\s*$")
NAME_SPLIT_PATTERN = re.compile(r"\s*[-–—]\s*")


@dataclass
class ControlMetadata:
    domain: str
    section: str | None
    description: str | None
    label: str
    code: str | None
    category: str | None
    search_keys: tuple[str, ...]


@dataclass
class ImportStats:
    """Simple data class capturing import outcomes."""

    created: int = 0
    updated: int = 0
    errors: list[str] = field(default_factory=list)


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

        domain_candidates = [candidate for candidate in (metadata.domain, *metadata.search_keys) if candidate]

        match_filters: list[Any] = []
        if domain_candidates:
            match_filters.append(Control.domain.in_(domain_candidates))
            match_filters.append(Control.section.in_(domain_candidates))
        if metadata.description:
            match_filters.append(Control.description == metadata.description)

        matching_controls: list[Control] = []
        if match_filters:
            condition = match_filters[0] if len(match_filters) == 1 else or_(*match_filters)
            matching_controls = list(
                db.session.execute(select(Control).where(condition)).scalars()
            )

        if not matching_controls:
            control = Control(
                section=metadata.section or metadata.domain,
                domain=metadata.domain,
                description=metadata.description,
            )
            db.session.add(control)
            db.session.flush()

            template = AssessmentTemplate(
                control=control,
                name=" ".join(part for part in (metadata.section, metadata.domain) if part).strip() or metadata.domain,
                version="1.0",
                question_set=AssessmentTemplate.default_question_set(),
            )
            db.session.add(template)
            stats.created += 1
        else:
            preferred_control = next(
                (item for item in matching_controls if item.domain == metadata.domain),
                matching_controls[0],
            )

            for item in matching_controls:
                item.description = metadata.description
                item.section = metadata.section or item.section
                if preferred_control is item:
                    item.domain = metadata.domain

            stats.updated += len(matching_controls)

    db.session.commit()
    return stats


def import_controls_from_file(path: Path | str) -> ImportStats:
    """Import controls from a JSON file path."""

    resolved = Path(path)
    with resolved.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return import_controls_from_mapping(payload)
