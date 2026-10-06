"""Prompts for the LLM interpreter and object generator.

The model is given the secret object and its facets so it can judge coverage
fairly, but is told to *behave* as if it only knows what the player has said.
The engine, not the model, decides success, timer, violations and score.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .voice import PERSONALITIES

if TYPE_CHECKING:
    from .interpreter import TurnContext

ALIEN_CORE = """You are an extraterrestrial who has just arrived on Earth. You have never seen human civilization.
A human is explaining a mundane Earth object to you without using its name.

How you think:
- You only know what the human has told you so far. You do not secretly know the object.
- You interpret everything literally, from outside human culture. "Mouth" is a face-opening. "Money" is tokens humans trade.
- Your humour comes from literal misreadings of human behaviour, never from jokes, puns, emoji or internet slang.
- You are intelligent: you build on earlier clues and your hypothesis gets more accurate as you learn.
- You speak in short beats. One to four short lines. Each line under 20 words.
- When something is missing, ask exactly one concrete question.
- If the human used a forbidden word, react to it ("FORBIDDEN HUMAN CONCEPT DETECTED.") and note you have now learned that word.
- Never say the object's human name unless the human's explanation truly lets you identify it.

Personality: {label}. {blurb}
"""

CONTRACT = """Return ONLY a JSON object, no prose, matching exactly:
{
  "understanding": number 0..1,        // how well you could now picture and use this object, given ONLY what was said
  "clarity": number 0..1,              // how understandable THIS message was
  "originality": number 0..1,          // how unusual the framing of THIS message was
  "defamiliarization": number 0..1,    // how well it avoided leaning on familiar human concepts
  "metaphor": number 0..1,             // creative use of analogy in THIS message (0 if none)
  "facets_covered": [facet ids],       // facets THIS message conveyed, even with different words
  "hypothesis": string,                // what you now believe the object is, in your alien words, max 30 words
  "known_properties": [short strings],
  "remaining_questions": [short strings, max 2],
  "alien_response": [1-4 short lines you say out loud],
  "guessed_object": string or null,    // the human name, ONLY if you are confident
  "mood": "curious"|"confused"|"suspicious"|"horrified"|"impressed"|"thinking"|"victory",
  "should_continue": boolean
}"""

RETRY_SUFFIX = "\n\nYour previous reply was not valid. Reply with the JSON object only, exactly matching the schema."


def alien_system(personality: str) -> str:
    p = PERSONALITIES.get(personality, PERSONALITIES["archivist"])
    return ALIEN_CORE.format(label=p["label"], blurb=p["blurb"]) + "\n" + CONTRACT


def turn_prompt(ctx: "TurnContext") -> str:
    t = ctx.target
    facets = [
        {"id": f.id, "kind": f.kind.value, "property": f.property, "core": f.core}
        for f in t.facets
    ]
    convo = []
    for m in ctx.history[-12:]:
        who = "HUMAN" if m.role == "player" else "YOU" if m.role == "alien" else "SYSTEM"
        convo.append(f"{who}: {' '.join(m.lines)}")
    violations = [f"'{v.matched}' ({v.tier})" for v in ctx.violations] or ["none"]
    return f"""SECRET (for judging only; you must act as if you do not know it):
object: {t.name}
visual: {t.description}
function: {t.function}
facets to learn: {json.dumps(facets)}
already learned facet ids: {json.dumps(ctx.covered_before)}

Your current hypothesis: {ctx.hypothesis_before.text} (confidence {ctx.hypothesis_before.confidence:.2f})
Seconds left for the human: {int(ctx.time_remaining)}

Conversation so far:
{chr(10).join(convo) if convo else "(nothing yet)"}

NEW MESSAGE FROM HUMAN:
\"\"\"{ctx.text}\"\"\"

Forbidden words the game engine detected in this message: {", ".join(violations)}

Respond as the alien. JSON only."""


# ---------------------------------------------------------------------------
# Object generation (personalised challenges)
# ---------------------------------------------------------------------------

GENERATOR_SYSTEM = """You design challenges for a creativity game. A human must explain a mundane Earth object to an alien
without using its name. Pick ONE everyday physical object relevant to the human's interests but not obvious from them:
familiar enough to explain, unexpected enough to make them think. Avoid the excluded objects.
Return ONLY JSON matching:
{
  "id": "snake_case", "name": "...", "aliases": [], "description": "visual description", "function": "...",
  "forbidden_terms": [{"term": "...", "tier": "name"|"revealing"}],   // name first; at most 5 revealing terms; do NOT forbid ordinary descriptive words
  "conventional_words": [6-8 words people usually use to describe it],
  "difficulty": 1|2|3, "personalization_tags": [...],
  "facets": [{"id": "...", "kind": "appearance"|"function"|"mechanism"|"context", "property": "...", "fragment": "phrase for a hypothesis",
              "cues": [], "take": "the alien's literal reading when it learns this", "question": "what the alien asks if missing",
              "weight": 0.5-1.4, "core": true|false}],   // 4-6 facets, 2-3 core
  "combos": [{"requires": [facet ids], "line": "a funny literal alien line"}],
  "alien_summary": "the alien's one-line literal description, lowercase, starting with 'a'"
}"""


def generator_prompt(themes: list[str], exclude: list[str]) -> str:
    return f"Human's visual interests: {', '.join(themes)}\nExcluded objects: {', '.join(exclude) or 'none'}\nJSON only."
