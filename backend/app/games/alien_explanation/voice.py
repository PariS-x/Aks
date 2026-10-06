"""The alien's stock phrases, per personality.

Object-specific lines live in the catalog (facet takes, combos). These are the
connective tissue: confusion, forbidden-word reactions, questions, verdicts.
"""

from __future__ import annotations

import random

PERSONALITIES: dict[str, dict] = {
    "archivist": {
        "label": "The Archivist",
        "blurb": "Literal. Patient. Keeps meticulous notes on your species.",
        "confused": [
            "I do not understand this object.",
            "That explanation has made things worse.",
            "I have recorded your words. They did not help.",
            "Interesting. But no.",
        ],
        "short": ["That is not enough words.", "Continue. I am patient. Within limits."],
        "repeat": ["You have told me this already.", "Yes. You said that. I wrote it down the first time."],
        "forbidden": ["FORBIDDEN HUMAN CONCEPT DETECTED.", "You used a forbidden human concept."],
        "ask": ["I require clarification.", "One thing remains unclear.", "Question."],
        "formed": ["I have formed a hypothesis.", "Interesting.", "Noted."],
        "closing": ["Humans are extremely strange.", "I will add this to the archive."],
        "fail_closing": ["I will take this misunderstanding home with me.", "The archive will have a gap."],
    },
    "skeptic": {
        "label": "The Skeptic",
        "blurb": "Suspicious of your species and everything it has built.",
        "confused": [
            "I do not believe you.",
            "That is not an object. That is a sentence.",
            "You are being vague on purpose.",
            "Your species invented this voluntarily?",
        ],
        "short": ["Insufficient.", "Is that all? Suspicious."],
        "repeat": ["You are repeating yourself. Humans do this when lying.", "Again? I heard you."],
        "forbidden": ["FORBIDDEN HUMAN CONCEPT DETECTED.", "Cheating. I saw that."],
        "ask": ["Explain this, if you can:", "I have a problem with your story."],
        "formed": ["Fine. I have a theory.", "Hm."],
        "closing": ["I remain suspicious of your species.", "Humans are extremely strange. And possibly dangerous."],
        "fail_closing": ["As I suspected. Nobody can explain this.", "I will assume it is a weapon."],
    },
    "enthusiast": {
        "label": "The Enthusiast",
        "blurb": "Delighted by everything. Understands little of it.",
        "confused": [
            "Fascinating. I understand nothing.",
            "Wonderful. What?",
            "I love this. I do not know what it is.",
        ],
        "short": ["More, please.", "Tell me more. Tell me everything."],
        "repeat": ["You said that already, and it was beautiful the first time."],
        "forbidden": ["FORBIDDEN HUMAN CONCEPT DETECTED. Thrilling.", "A forbidden word! How daring."],
        "ask": ["Oh. Oh! But tell me:", "Wait, wait:"],
        "formed": ["I have a hypothesis! It is exciting.", "Ooh."],
        "closing": ["Your species is fascinating.", "I would like to own several."],
        "fail_closing": ["I did not understand, but I enjoyed it enormously.", "Mysterious. I love it."],
    },
}


class Voice:
    def __init__(self, personality: str, seed: str):
        self.p = PERSONALITIES.get(personality, PERSONALITIES["archivist"])
        self.rng = random.Random(seed)

    def pick(self, bank: str) -> str:
        return self.rng.choice(self.p[bank])
