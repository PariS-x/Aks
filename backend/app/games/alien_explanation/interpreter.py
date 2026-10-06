"""Interpreters turn one player message into a validated `Interpretation`.

Two implementations share one contract:

* `OfflineInterpreter` - deterministic, cue-based. Powers demo mode with no
  API key, and is always computed as a sanity anchor.
* `LLMInterpreter` - asks a language model to *be* the alien and return strict
  JSON. Its output is validated, clamped and filtered before the engine sees it.

Neither one changes game state. The engine decides what to accept.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional, Protocol

from pydantic import ValidationError

from ...llm.client import LLMClient, LLMError
from . import prompts
from .features import conventional_ratio, extract, overlap
from .models import AlienHypothesis, Interpretation, Message, Mood, TargetObject, Violation
from .voice import Voice


@dataclass
class TurnContext:
    target: TargetObject
    history: list[Message]
    text: str
    violations: list[Violation]
    covered_before: list[str]
    hypothesis_before: AlienHypothesis
    understanding_before: float
    personality: str
    seed: str
    last_question_facet: Optional[str]
    time_remaining: float


class Interpreter(Protocol):
    name: str

    async def interpret(self, ctx: TurnContext) -> Interpretation: ...


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def coverage_understanding(target: TargetObject, covered: set[str]) -> float:
    total = sum(f.weight for f in target.facets)
    got = sum(f.weight for f in target.facets if f.id in covered)
    u = got / total if total else 0.0
    cores = [f.id for f in target.facets if f.core]
    if all(c in covered for c in cores):
        return min(1.0, u * 1.2 + 0.05)
    return min(u, 0.72)


def compose_hypothesis(target: TargetObject, covered: set[str]) -> str:
    idx = {f.id: i for i, f in enumerate(target.facets)}
    known = [f for f in target.facets if f.id in covered]
    if not known:
        return "Unknown. Possibly food. Possibly a weapon."
    order = {"appearance": 0, "context": 1, "function": 2, "mechanism": 3}
    known.sort(key=lambda f: (order[f.kind.value], idx[f.id]))
    looks = [f for f in known if f.kind.value == "appearance"]
    rest = [f for f in known if f.kind.value != "appearance"]
    head = " ".join(f.fragment for f in looks) if looks else "an object"
    text = ", ".join([head] + [f.fragment for f in rest])
    return (text[0].upper() + text[1:]).rstrip(".") + "."


def previous_player_stems(history: list[Message]) -> list[str]:
    out: list[str] = []
    for m in history:
        if m.role == "player":
            out += extract(" ".join(m.lines)).content_stems
    return out


# ---------------------------------------------------------------------------
# Offline interpreter
# ---------------------------------------------------------------------------


class OfflineInterpreter:
    name = "offline"

    def match_facets(self, target: TargetObject, text: str) -> list[str]:
        """Facet ids mentioned in `text`, in the order the player raised them."""
        low = text.lower()
        found: list[tuple[int, str]] = []
        for f in target.facets:
            pos = [m.start() for c in f.cues if (m := re.search(c, low))]
            if pos:
                found.append((min(pos), f.id))
        return [fid for _, fid in sorted(found)]

    def metrics(self, target: TargetObject, text: str, history: list[Message]) -> dict:
        tf = extract(text)
        prev = previous_player_stems(history)
        redundancy = overlap(tf.content_stems, prev)
        conv = conventional_ratio(tf, target.conventional_words)
        n = tf.n
        length_ok = 1.0 if 6 <= n <= 80 else (n / 6 if n < 6 else max(0.4, 80 / n))
        per_sentence = n / tf.sentences
        sentence_ok = 1.0 if per_sentence <= 28 else max(0.5, 28 / per_sentence)
        metaphor = min(1.0, len(tf.metaphors) * 0.45 + (0.15 if tf.outsider else 0))
        originality = min(1.0, 0.25 + tf.rare_ratio * 1.4 + tf.type_token * 0.25 + metaphor * 0.25 - redundancy * 0.35)
        defam = min(1.0, max(0.0, 0.6 - conv * 1.0 + min(tf.outsider, 3) * 0.12 + metaphor * 0.25 + tf.rare_ratio * 0.5))
        return dict(
            tf=tf, redundancy=redundancy, length_ok=length_ok, sentence_ok=sentence_ok,
            metaphor=metaphor, originality=max(0.0, originality), defamiliarization=defam,
        )

    async def interpret(self, ctx: TurnContext) -> Interpretation:
        t = ctx.target
        v = Voice(ctx.personality, ctx.seed)
        hit = self.match_facets(t, ctx.text)
        before = set(ctx.covered_before)
        after = before | set(hit)
        new = [fid for fid in hit if fid not in before]
        m = self.metrics(t, ctx.text, ctx.history)
        u = coverage_understanding(t, after)
        gain = max(0.0, u - ctx.understanding_before)
        clarity = min(1.0, 0.35 + gain * 1.6 + 0.1 * len(hit)) * m["length_ok"] * m["sentence_ok"]

        cores = [f.id for f in t.facets if f.core]
        solved = u >= 0.8 and all(c in after for c in cores)
        lines: list[str] = []

        if ctx.violations:
            lines.append(v.pick("forbidden"))
            word = ctx.violations[0].matched.lower()
            lines.append("Nice try." if ctx.violations[0].evasion else f"I now know what a '{word}' is.")

        new_combos = [c for c in t.combos if set(c.requires) <= after and not set(c.requires) <= before]
        if new_combos:
            lines += new_combos[0].line.split(" | ")
        elif new:
            best = sorted((t.facet(fid) for fid in new), key=lambda f: -f.weight)
            for f in best[:2]:
                if f.take:
                    lines += f.take.split(" | ")
            if len(lines) == (2 if ctx.violations else 0):
                lines.append(v.pick("formed"))
        elif solved:
            pass
        elif m["tf"].n < 4:
            lines.append(v.pick("short"))
        elif m["redundancy"] > 0.6:
            lines.append(v.pick("repeat"))
        else:
            lines.append(v.pick("confused"))

        if solved:
            lines = lines[-3:] + ["WAIT."]

        missing = [f for f in t.facets if f.core and f.id not in after and f.question]
        if not missing:
            missing = [f for f in t.facets if f.id not in after and f.question]
        if not solved and missing and len(new) <= 1:
            # Rotate questions so the alien does not nag about the same thing
            q = next((f for f in missing if f.id != ctx.last_question_facet), missing[0])
            lines += [v.pick("ask"), q.question]

        if ctx.violations:
            mood = Mood.horrified
        elif solved:
            mood = Mood.victory
        elif new_combos or (len(new) >= 2 and m["originality"] > 0.55):
            mood = Mood.impressed
        elif not new and m["tf"].n >= 25:
            mood = Mood.suspicious
        elif not new:
            mood = Mood.confused
        else:
            mood = Mood.thinking

        return Interpretation(
            understanding=u,
            clarity=clarity,
            originality=m["originality"],
            defamiliarization=m["defamiliarization"],
            metaphor=m["metaphor"],
            facets_covered=hit,
            hypothesis=compose_hypothesis(t, after),
            known_properties=[f.property for f in t.facets if f.id in after],
            remaining_questions=[f.question for f in missing[:2]],
            alien_response=lines[:5] or ["..."],
            guessed_object=t.name if solved else None,
            mood=mood,
            should_continue=not solved,
        )


# ---------------------------------------------------------------------------
# LLM interpreter
# ---------------------------------------------------------------------------

_JSON_BLOCK = re.compile(r"\{.*\}", re.S)


def parse_interpretation(raw: str, target: TargetObject) -> Interpretation:
    m = _JSON_BLOCK.search(raw)
    if not m:
        raise LLMError("no JSON object in model output")
    data = json.loads(m.group(0))
    if isinstance(data.get("alien_response"), str):
        data["alien_response"] = [s for s in re.split(r"(?<=[.?!])\s+", data["alien_response"]) if s]
    interp = Interpretation.model_validate(data)
    valid = {f.id for f in target.facets}
    interp.facets_covered = [fid for fid in interp.facets_covered if fid in valid]
    return interp


class LLMInterpreter:
    name = "llm"

    def __init__(self, client: LLMClient):
        self.client = client

    async def interpret(self, ctx: TurnContext) -> Interpretation:
        system = prompts.alien_system(ctx.personality)
        user = prompts.turn_prompt(ctx)
        last_err: Exception | None = None
        for attempt in range(2):
            raw = await self.client.complete(system, user if attempt == 0 else user + prompts.RETRY_SUFFIX, max_tokens=700)
            try:
                return parse_interpretation(raw, ctx.target)
            except (ValidationError, ValueError, LLMError) as e:
                last_err = e
        raise LLMError(f"model output failed validation twice: {last_err}")
