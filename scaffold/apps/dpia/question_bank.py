"""Canonical DPIA / FRIA questions imported from the legacy form."""

from __future__ import annotations

DEFAULT_QUESTIONS = [
    {
        "text_key": "dpia.questions.processing_goal.text",
        "help_key": "dpia.questions.processing_goal.help",
        "text": "Beschrijf in het kort het doel van de gegevensverwerking.",
        "category": "Algemeen",
        "help_text": "Welk probleem lost dit op? Wat is het beoogde resultaat?",
        "question_type": "TextArea",
        "sort_order": 1,
    },
    {
        "text_key": "dpia.questions.personal_data.text",
        "help_key": "dpia.questions.personal_data.help",
        "text": "Worden er persoonsgegevens verwerkt?",
        "category": "Algemeen",
        "help_text": "Alle informatie over een geïdentificeerde of identificeerbare natuurlijke persoon.",
        "question_type": "YesNo",
        "sort_order": 2,
    },
    {
        "text_key": "dpia.questions.ai_usage.text",
        "help_key": "dpia.questions.ai_usage.help",
        "text": "Wordt er voor de verwerking gebruik gemaakt van een vorm van Artificiële Intelligentie (AI)?",
        "category": "Algemeen",
        "help_text": "Denk aan machine learning, neurale netwerken, etc.",
        "question_type": "YesNo",
        "sort_order": 3,
    },
    {
        "text_key": "dpia.questions.special_categories.text",
        "help_key": "dpia.questions.special_categories.help",
        "text": "Worden er bijzondere categorieën van persoonsgegevens verwerkt?",
        "category": "DPIA",
        "help_text": "Bijv. gezondheid, ras, politieke opvatting, etc.",
        "question_type": "YesNo",
        "sort_order": 10,
    },
    {
        "text_key": "dpia.questions.large_scale.text",
        "help_key": "dpia.questions.large_scale.help",
        "text": "Vindt er grootschalige verwerking plaats?",
        "category": "DPIA",
        "help_text": "Is de verwerking gericht op een groot aantal betrokkenen of omvat het een grote hoeveelheid gegevens?",
        "question_type": "YesNo",
        "sort_order": 11,
    },
    {
        "text_key": "dpia.questions.automated_decisions.text",
        "help_key": "dpia.questions.automated_decisions.help",
        "text": "Neemt het systeem zelfstandig beslissingen met aanzienlijke gevolgen voor een persoon?",
        "category": "FRIA",
        "help_text": "Bijv. automatische afwijzing van een sollicitatie, lening of verzekering.",
        "question_type": "YesNo",
        "sort_order": 22,
    },
]
