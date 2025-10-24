"""Assessment-related forms."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional


class AssessmentStartForm(FlaskForm):
    template_id = SelectField("Sjabloon", coerce=int, validators=[DataRequired(message="Kies een sjabloon.")])
    submit = SubmitField("Start self-assessment")


class AssessmentAssignForm(FlaskForm):
    assignee_id = SelectField(
        "Toewijzen aan",
        coerce=int,
        validators=[DataRequired(message="Selecteer een gebruiker.")],
    )
    template_id = SelectField(
        "Sjabloon",
        coerce=int,
        validators=[DataRequired(message="Kies een sjabloon.")],
    )
    due_date = DateField("Vervaldatum", validators=[Optional()], format="%Y-%m-%d")
    submit = SubmitField("Toewijzen")


class AssessmentResponseForm(FlaskForm):
    save = SubmitField("Antwoorden opslaan")
    submit_for_review = SubmitField("Ter beoordeling indienen")


class AssessmentReviewForm(FlaskForm):
    comment = TextAreaField(
        "Reviewopmerking",
        render_kw={
            "rows": 4,
            "placeholder": "Geef toelichting bij afkeuren of aanvullende context bij goedkeuren.",
        },
    )
    approve = SubmitField("Goedkeuren")
    return_to_assignee = SubmitField("Terug naar indiener")


def build_assessment_response_form(question_set: Dict[str, Any]) -> Tuple[type[AssessmentResponseForm], List[Dict[str, Any]]]:
    """Generate a dynamic form for an assessment question set.

    Returns a tuple containing the generated form class and a layout description
    so templates can render sections in order.
    """

    class DynamicAssessmentResponseForm(AssessmentResponseForm):
        pass

    layout: List[Dict[str, Any]] = []

    for dimension_key, section in question_set.items():
        questions = section.get("questions", []) or []
        rendered_questions: List[Dict[str, Any]] = []

        for index, question_text in enumerate(questions):
            field_name = f"{dimension_key}_{index}"
            field = TextAreaField(
                question_text,
                render_kw={
                    "rows": 3,
                    "placeholder": "Typ het antwoord hier.",
                },
            )
            setattr(DynamicAssessmentResponseForm, field_name, field)
            rendered_questions.append(
                {
                    "field_name": field_name,
                    "dimension": dimension_key,
                    "question": question_text,
                }
            )

        layout.append(
            {
                "dimension": dimension_key,
                "label": section.get("label") or dimension_key.replace("_", " ").title(),
                "questions": rendered_questions,
            }
        )

    return DynamicAssessmentResponseForm, layout
