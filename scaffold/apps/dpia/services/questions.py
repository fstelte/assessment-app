"""Utility helpers to provision DPIA / FRIA question data."""

from __future__ import annotations

import logging

import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError

from ....extensions import db
from ..models import DPIAQuestion
from ..question_bank import DEFAULT_QUESTIONS

logger = logging.getLogger(__name__)


def ensure_default_questions() -> int:
    """Ensure the canonical question bank exists; return how many rows were inserted."""

    try:
        existing_questions = db.session.scalars(sa.select(DPIAQuestion)).all()
    except (ProgrammingError, OperationalError):  # pragma: no cover - occurs before migrations
        db.session.rollback()
        logger.debug("Skipping DPIA question provisioning; table not ready yet.")
        return 0

    by_key: dict[str, DPIAQuestion] = {}
    by_text: dict[str, DPIAQuestion] = {}
    for question in existing_questions:
        if question.text_key:
            by_key[question.text_key] = question
        if question.text:
            by_text[question.text] = question

    inserted = 0
    updated = False

    for spec in DEFAULT_QUESTIONS:
        identifier = spec.get("text_key")
        question = None
        if identifier:
            question = by_key.get(identifier)
        if question is None:
            question = by_text.get(spec["text"])

        if question is None:
            question = DPIAQuestion(
                text=spec["text"],
                text_key=spec.get("text_key"),
                category=spec["category"],
                help_text=spec.get("help_text"),
                help_key=spec.get("help_key"),
                question_type=spec.get("question_type", "text"),
                sort_order=spec.get("sort_order"),
            )
            db.session.add(question)
            inserted += 1
            continue

        for attr in ("text", "category", "help_text", "help_key", "question_type", "sort_order"):
            new_value = spec.get(attr)
            if new_value is not None and getattr(question, attr) != new_value:
                setattr(question, attr, new_value)
                updated = True

        if spec.get("text_key") and question.text_key != spec["text_key"]:
            question.text_key = spec["text_key"]
            updated = True

    if inserted or updated:
        db.session.commit()
        if inserted:
            logger.info("Seeded %s DPIA question(s)", inserted)
        if updated and not inserted:
            logger.info("Updated DPIA question metadata for translations")
    return inserted
