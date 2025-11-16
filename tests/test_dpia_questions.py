from scaffold.apps.dpia.models import DPIAQuestion
from scaffold.apps.dpia.question_bank import DEFAULT_QUESTIONS
from scaffold.apps.dpia.services.questions import ensure_default_questions
from scaffold.extensions import db


def test_default_questions_seeded_once(app):
    with app.app_context():
        inserted = ensure_default_questions()
        assert inserted == len(DEFAULT_QUESTIONS)
        questions = DPIAQuestion.query.all()
        assert len(questions) == len(DEFAULT_QUESTIONS)
        expected_keys = {spec["text_key"] for spec in DEFAULT_QUESTIONS}
        assert {question.text_key for question in questions} == expected_keys

        inserted_again = ensure_default_questions()
        assert inserted_again == 0
        assert DPIAQuestion.query.count() == len(DEFAULT_QUESTIONS)


def test_question_metadata_updated_when_missing(app):
    with app.app_context():
        ensure_default_questions()
        question = DPIAQuestion.query.first()
        original_id = question.id
        question.text_key = None
        question.help_key = None
        question.question_type = "Legacy"
        db.session.commit()

        ensure_default_questions()

        refreshed = db.session.get(DPIAQuestion, original_id)
        spec = next(spec for spec in DEFAULT_QUESTIONS if spec["text"] == refreshed.text)
        assert refreshed.text_key == spec["text_key"]
        assert refreshed.help_key == spec["help_key"]
        assert refreshed.question_type == spec.get("question_type", "text")
