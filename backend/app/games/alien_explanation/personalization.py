"""Choosing the specimen.

"Familiar enough to understand. Unexpected enough to make them think."

Objects are scored against the player's themes, but the very best literal
match is not always chosen: objects that touch one strong theme sideways get a
small bonus over objects that match everything, so a space-heavy board gets a
satellite dish or a seatbelt sometimes, not always a telescope.
"""

from __future__ import annotations

import random
from typing import Optional

from ...llm.client import LLMClient
from ...profile.models import VisualProfile
from . import catalog, prompts
from .models import Personalization, TargetObject

REASONS = {
    "space": "You collect images of things very far away. This object is about distance too, in its way.",
    "architecture": "You save buildings. This object lives inside or beside them.",
    "robotics": "You collect machines. Here is a smaller, stupider machine.",
    "travel": "You save images of elsewhere. This object goes elsewhere with you.",
    "fashion": "You save garments. This object is attached to them, or to you.",
    "food": "You save food. This object stands between you and food.",
    "music": "You save sound in picture form. This object is closer to the source.",
    "nature": "You save outdoor images. This object is how humans negotiate with the outdoors.",
    "interiors": "You save rooms. This object lives in one.",
    "tech": "You save devices. This one is so ordinary you have stopped seeing it.",
    "cars": "You save vehicles. This object rides along.",
    "cities": "You save streets. This object is part of how streets behave.",
    "photography": "You save images of images. This object will test your eye.",
    "wellness": "You save rituals. This object is part of one.",
    "diy": "You save tools. Here is one you have held a thousand times.",
    "film": "You save scenes. This object is in the background of most of them.",
    "words": "You save words. Here is an object no one has ever described properly. Try.",
    "philosophy": "You save thoughts about existence. This object exists. Explain why.",
    "melancholy": "Your archive is quiet and a little sad. This object keeps humans company in that weather.",
    "love": "You save images about attachment. This object is how humans let each other in.",
    "everyday": "This object is in your life. You have never had to explain it.",
}


def select_object(
    profile: Optional[VisualProfile],
    exclude: list[str] | None = None,
    difficulty: Optional[int] = None,
    seed: Optional[str] = None,
) -> tuple[TargetObject, Personalization]:
    rng = random.Random(seed)
    exclude = set(exclude or [])
    pool = [o for o in catalog.CATALOG if o.id not in exclude] or list(catalog.CATALOG)
    if difficulty:
        pool = [o for o in pool if o.difficulty == difficulty] or pool

    if not profile or not profile.themes:
        obj = rng.choice(pool)
        return catalog.get(obj.id), Personalization(themes=[], reason="I have selected an object at random. It seemed suspicious.", source="none")

    weights = {t.name: t.weight for t in profile.themes}
    scored = []
    for o in pool:
        matches = [weights[t] for t in o.personalization_tags if t in weights]
        if not matches:
            s = 0.05  # still possible: a little chaos keeps it unexpected
        else:
            # Strongest single link counts most; piling up matches has diminishing returns
            s = max(matches) + 0.25 * (sum(matches) - max(matches))
            if len(matches) == 1:
                s += 0.12  # sideways relevance bonus
        scored.append((s + rng.random() * 0.15, o))
    scored.sort(key=lambda x: -x[0])
    top = scored[:4]
    pick = rng.choices([o for _, o in top], weights=[max(0.01, s) for s, _ in top])[0]

    linked = [t for t in profile.top_themes(5) if t.name in pick.personalization_tags]
    reason_theme = linked[0].name if linked else "everyday"
    return catalog.get(pick.id), Personalization(
        themes=[t.label for t in profile.top_themes(4)],
        reason=REASONS.get(reason_theme, REASONS["everyday"]),
        source="demo" if profile.source == "demo" else "pinterest" if profile.source == "pinterest" else "manual",
    )


async def generate_object(client: LLMClient, profile: VisualProfile, exclude: list[str]) -> Optional[TargetObject]:
    """Ask the model for a fresh, personalised specimen. Validated or discarded."""
    import json
    import re

    try:
        raw = await client.complete(
            prompts.GENERATOR_SYSTEM,
            prompts.generator_prompt([t.name for t in profile.top_themes(5)], exclude + [o.name for o in catalog.CATALOG]),
            max_tokens=1400,
        )
        data = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
        data["generated"] = True
        data["image_url"] = ""
        from .constraints import stem
        from .features import COMMON

        for fct in data.get("facets", []):
            # Model-written regexes are not trusted. Derive simple word cues
            # from the facet's own description as an offline fallback.
            words = re.findall(r"[a-z]+", f"{fct.get('property', '')} {fct.get('fragment', '')}".lower())
            fct["cues"] = sorted({rf"\b{re.escape(stem(w))}" for w in words if len(w) > 3 and w not in COMMON})
        obj = TargetObject.model_validate(data)
        if obj.forbidden_terms[0].tier != "name":
            return None
        obj.forbidden_terms[0].visible = False
        return obj
    except Exception:
        return None
