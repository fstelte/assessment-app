"""Forms supporting CSA self-assessment workflows."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, cast

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional

from scaffold.core.i18n import gettext as _, lazy_gettext as _l


DIMENSION_LABEL_KEYS: Dict[str, str] = {
    "design": "csa.assessments.questions.design.label",
    "operation": "csa.assessments.questions.operation.label",
    "monitoring_improvement": "csa.assessments.questions.monitoring.label",
}

LEGACY_LABEL_KEY_BY_TEXT: Dict[str, str] = {
    "Ontwerp van de Beheersmaatregel": DIMENSION_LABEL_KEYS["design"],
    "Control design": DIMENSION_LABEL_KEYS["design"],
    "Werking van de Beheersmaatregel (bestaan)": DIMENSION_LABEL_KEYS["operation"],
    "Control operation": DIMENSION_LABEL_KEYS["operation"],
    "Monitoring en Verbetering": DIMENSION_LABEL_KEYS["monitoring_improvement"],
    "Monitoring en verbetering": DIMENSION_LABEL_KEYS["monitoring_improvement"],
    "Monitoring and improvement": DIMENSION_LABEL_KEYS["monitoring_improvement"],
}

LEGACY_QUESTION_KEY_BY_TEXT: Dict[str, Dict[str, str]] = {
    "design": {
        "Is de beheersmaatregel duidelijk en ondubbelzinnig gedocumenteerd in een vastgesteld beleidsdocument of procedure?": "csa.assessments.questions.design.q1",
        "Is the control clearly and unambiguously documented in an approved policy or procedure?": "csa.assessments.questions.design.q1",
        "Is er een duidelijke 'control owner' toegewezen die eindverantwoordelijk is voor deze maatregel?": "csa.assessments.questions.design.q2",
        "Is a clear control owner assigned who has ultimate accountability for this control?": "csa.assessments.questions.design.q2",
        "Zijn de rollen en verantwoordelijkheden voor de uitvoering van de maatregel duidelijk beschreven en toegewezen?": "csa.assessments.questions.design.q3",
        "Are the roles and responsibilities for executing the control clearly described and assigned?": "csa.assessments.questions.design.q3",
    },
    "operation": {
        "Is de beheersmaatregel in de afgelopen periode consequent uitgevoerd zoals beschreven?": "csa.assessments.questions.operation.q1",
        "Has the control been executed consistently according to the procedure during the recent period?": "csa.assessments.questions.operation.q1",
        "Kunt u bewijs overleggen waaruit de consistente uitvoering van de maatregel blijkt (bv. logs, rapportages, screenshots)?": "csa.assessments.questions.operation.q2",
        "Kunt u bewijs overleggen waaruit de consistente uitvoering van de maatregel blijkt (bijvoorbeeld logs, rapportages, screenshots)?": "csa.assessments.questions.operation.q2",
        "Can you provide evidence demonstrating consistent execution of the control (e.g. logs, reports, screenshots)?": "csa.assessments.questions.operation.q2",
        "Zijn eventuele afwijkingen of uitzonderingen op de procedure gedocumenteerd en geautoriseerd?": "csa.assessments.questions.operation.q3",
        "Are any deviations or exceptions from the procedure documented and approved?": "csa.assessments.questions.operation.q3",
    },
    "monitoring_improvement": {
        "Wordt de effectiviteit van deze maatregel periodiek gemonitord en gerapporteerd aan de 'control owner'?": "csa.assessments.questions.monitoring.q1",
        "Is the effectiveness of this control monitored and reported to the control owner on a periodic basis?": "csa.assessments.questions.monitoring.q1",
        "Is de maatregel in het afgelopen jaar geëvalueerd om te bepalen of deze nog steeds effectief en efficiënt is?": "csa.assessments.questions.monitoring.q2",
        "Has the control been evaluated within the past year to confirm that it remains effective and efficient?": "csa.assessments.questions.monitoring.q2",
        "Zijn er verbeteracties geïdentificeerd en geïmplementeerd op basis van de evaluatie of geïdentificeerde afwijkingen?": "csa.assessments.questions.monitoring.q3",
        "Zijn er verbeteracties geïdentificeerd en geïmplementeerd op basis van de evaluatie of geconstateerde afwijkingen?": "csa.assessments.questions.monitoring.q3",
        "Have improvement actions been identified and implemented based on evaluations or detected deviations?": "csa.assessments.questions.monitoring.q3",
    },
}


def _label(key: str) -> str:
    """Return a lazy translation coerced to str for WTForms labels."""

    # Return lazy translation so the label is resolved at render time (per-request)
    return cast(str, _l(key))


def _message(key: str) -> str:
    """Return a lazy translation coerced to str for validation messages."""

    return cast(str, _l(key))


def _resolve_label_key(dimension_key: str, section: Dict[str, Any]) -> str | None:
    label_key = section.get("label_key")
    if label_key:
        return str(label_key)

    label_text = section.get("label")
    if isinstance(label_text, str):
        mapped = LEGACY_LABEL_KEY_BY_TEXT.get(label_text)
        if mapped:
            return mapped

    return DIMENSION_LABEL_KEYS.get(dimension_key)


def _resolve_question_text_key(dimension_key: str, text: str | None) -> str | None:
    if not text:
        return None
    mapping = LEGACY_QUESTION_KEY_BY_TEXT.get(dimension_key) or {}
    return mapping.get(text)


def localise_question_set(question_set: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return sections with translated labels and questions for the active locale."""

    sections: List[Dict[str, Any]] = []

    for dimension_key, section in question_set.items():
        label_key = _resolve_label_key(dimension_key, section)
        section_label = _(label_key) if label_key else section.get("label") or dimension_key.replace("_", " ").title()

        questions: List[Dict[str, Any]] = []
        raw_questions = section.get("questions", []) or []

        for index, question_spec in enumerate(raw_questions):
            question_text_key: str | None = None
            canonical_question: str | None = None
            fallback_text: str = ""

            if isinstance(question_spec, dict):
                question_text_key = question_spec.get("text_key")
                fallback_text = question_spec.get("text") or ""
                canonical_question = (
                    question_spec.get("id")
                    or fallback_text
                    or question_text_key
                    or f"{dimension_key}_{index}"
                )
            else:
                fallback_text = str(question_spec)
                canonical_question = fallback_text

            if not question_text_key:
                question_text_key = _resolve_question_text_key(dimension_key, fallback_text)
            if not question_text_key:
                question_text_key = _resolve_question_text_key(dimension_key, canonical_question)

            label_text = _(question_text_key) if question_text_key else (fallback_text or canonical_question or "")
            if not canonical_question:
                canonical_question = fallback_text or label_text or f"{dimension_key}_{index}"

            questions.append(
                {
                    "field_name": f"{dimension_key}_{index}",
                    "dimension": dimension_key,
                    "question": canonical_question,
                    "text_key": question_text_key,
                    "label": label_text,
                }
            )

        sections.append(
            {
                "dimension": dimension_key,
                "label": section_label,
                "label_key": label_key,
                "questions": questions,
            }
        )

    return sections


class AssessmentStartForm(FlaskForm):
    """Start a self-assessment from an active template."""

    template_id = SelectField(
        _label("csa.assessments.start.fields.template.label"),
        coerce=int,
        validators=[DataRequired(message=_message("csa.assessments.start.fields.template.required"))],
    )
    submit = SubmitField(_label("csa.assessments.start.submit"))


class AssessmentAssignForm(FlaskForm):
    """Assign an assessment template to another user."""

    assignee_id = SelectField(
        _label("csa.assessments.assign.fields.assignee.label"),
        coerce=int,
        validators=[DataRequired(message=_message("csa.assessments.assign.fields.assignee.required"))],
    )
    template_id = SelectField(
        _label("csa.assessments.assign.fields.template.label"),
        coerce=int,
        validators=[DataRequired(message=_message("csa.assessments.assign.fields.template.required"))],
    )
    due_date = DateField(
        _label("csa.assessments.assign.fields.due_date.label"),
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    submit = SubmitField(_label("csa.assessments.assign.submit"))


class AssessmentResponseForm(FlaskForm):
    """Shared actions for responding to an assessment."""

    save = SubmitField(_label("csa.assessments.detail.actions.save"))
    submit_for_review = SubmitField(_label("csa.assessments.detail.actions.submit_for_review"))


class AssessmentReviewForm(FlaskForm):
    """Form used by reviewers to approve or return assessments."""

    comment = TextAreaField(
        _label("csa.assessments.detail.review.comment_label"),
        render_kw={
            "rows": 4,
            "placeholder": _l("csa.assessments.detail.review.comment_placeholder"),
        },
    )
    approve = SubmitField(_label("csa.assessments.detail.review.approve"))
    return_to_assignee = SubmitField(_label("csa.assessments.detail.review.return_to_assignee"))


def build_assessment_response_form(question_set: Dict[str, Any]) -> Tuple[type[AssessmentResponseForm], List[Dict[str, Any]]]:
    """Generate a dynamic response form for the provided question set."""

    class DynamicAssessmentResponseForm(AssessmentResponseForm):  # type: ignore[misc]
        pass

    layout = localise_question_set(question_set)

    for section in layout:
        for question in section["questions"]:
            field = TextAreaField(
                question["label"],
                render_kw={
                    "rows": 3,
                    "placeholder": _l("csa.assessments.form.answer_placeholder"),
                },
            )
            setattr(DynamicAssessmentResponseForm, question["field_name"], field)

    return DynamicAssessmentResponseForm, layout
