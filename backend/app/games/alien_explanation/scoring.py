"""Score engine and end-of-round reflection.

Game metrics, not psychometrics. Every number carries a plain-language
evidence string so the result screen can show *why*, and every observation
points back at something the player actually wrote.
"""

from __future__ import annotations

import re
from statistics import mean

from .features import extract
from .models import GameScore, GameState, GameStatus, Observation, ScoreLine
from .voice import Voice

WEIGHTS = {
    "clarity": 0.2, "originality": 0.2, "defamiliarization": 0.2,
    "metaphor": 0.1, "constraint": 0.15, "comprehension": 0.15,
}


def _pct(x: float) -> int:
    return max(0, min(100, round(x * 100)))


def score(state: GameState) -> GameScore:
    turns = [m for m in state.player_turns() if m.metrics]
    ms = [m.metrics for m in turns] or []
    avg = lambda k: mean(getattr(x, k) for x in ms) if ms else 0.0  # noqa: E731

    clarity = _pct(0.6 * avg("clarity") + 0.4 * state.understanding)
    red = avg("redundancy")
    originality = _pct(avg("originality") * (1 - 0.3 * red))
    defam = _pct(avg("defamiliarization"))
    best_met = max((x.metaphor for x in ms), default=0.0)
    metaphor = _pct(0.6 * best_met + 0.4 * avg("metaphor"))

    names = sum(1 for v in state.violations if v.tier == "name")
    rev = sum(1 for v in state.violations if v.tier == "revealing")
    eva = sum(1 for v in state.violations if v.evasion)
    constraint = max(0, 100 - 25 * names - 12 * rev - 10 * eva)

    used = state.duration_s - state.time_remaining()
    left_frac = state.time_remaining() / state.duration_s if state.duration_s else 0
    n = len(turns)
    if state.status == GameStatus.success:
        comprehension = max(35, min(100, round(100 * (0.55 + 0.45 * left_frac)) - 6 * max(0, n - 1)))
    else:
        comprehension = round(60 * state.understanding)

    lines = [
        ScoreLine(key="clarity", label="Clarity", value=clarity,
                  evidence=f"The alien reached {round(state.understanding * 100)}% understanding over {n} transmission{'s' if n != 1 else ''}."),
        ScoreLine(key="originality", label="Originality", value=originality,
                  evidence=("You repeated yourself a lot." if red > 0.5 else "Measured from unusual vocabulary, variety and framing.")),
        ScoreLine(key="defamiliarization", label="Defamiliarization", value=defam,
                  evidence="How little you leaned on the usual words people use for this object."),
        ScoreLine(key="metaphor", label="Metaphor", value=metaphor,
                  evidence=_metaphor_evidence(state)),
        ScoreLine(key="constraint", label="Constraint", value=constraint,
                  evidence=("No forbidden words. Clean." if not state.violations else
                            f"{len(state.violations)} forbidden word{'s' if len(state.violations) != 1 else ''}: "
                            + ", ".join(sorted({v.matched.lower() for v in state.violations})))),
        ScoreLine(key="comprehension", label="Alien comprehension", value=comprehension,
                  evidence=(f"Understood in {round(used)}s and {n} message{'s' if n != 1 else ''}." if state.status == GameStatus.success
                            else "The alien never fully understood.")),
    ]
    final = round(sum(WEIGHTS[l.key] * l.value for l in lines))
    title, reason = _title(state, {l.key: l.value for l in lines}, final)
    return GameScore(lines=lines, final=final, title=title, title_reason=reason)


def _metaphor_evidence(state: GameState) -> str:
    found = []
    for m in state.player_turns():
        found += extract(" ".join(m.lines)).metaphors
    if not found:
        return "No analogies detected. Very literal."
    return f"{len(found)} analog{'y' if len(found) == 1 else 'ies'} detected."


def _title(state: GameState, s: dict[str, int], final: int) -> tuple[str, str]:
    n = len(state.player_turns())
    if len(state.violations) >= 3:
        return "The Forbidden Word Menace", "Three or more forbidden words. The alien now speaks fluent human."
    if state.status == GameStatus.success and n == 1 and final >= 75:
        return "The Alien Whisperer", "Understood in a single transmission."
    if s["metaphor"] >= 70:
        return "The Metaphor Machine", "You explained mostly by comparison."
    if s["defamiliarization"] >= 75 and s["originality"] >= 70:
        return "The Concept Bender", "You described it from a genuinely strange angle."
    if s["clarity"] >= 80 and s["originality"] < 55:
        return "The Human Dictionary", "Precise, correct, and not remotely poetic."
    if s["originality"] < 45 and s["defamiliarization"] < 45:
        return "The Extremely Literal Human", "You explained it the way a manual would."
    if final >= 82:
        return "The Master Explainer", "High across the board."
    if state.status == GameStatus.timeout and state.understanding < 0.5:
        return "The Mysterious Narrator", "The alien is still guessing."
    return "The Creative Translator", "A solid translation between species."


# ---------------------------------------------------------------------------
# AKS NOTICED
# ---------------------------------------------------------------------------


def observations(state: GameState) -> list[Observation]:
    turns = state.player_turns()
    if not turns:
        return [Observation(text="You said nothing. The alien respects mystery.", evidence="0 messages sent.")]
    texts = [" ".join(m.lines) for m in turns]
    feats = [extract(t) for t in texts]
    out: list[tuple[int, Observation]] = []

    # 1. Function vs appearance first
    from .interpreter import OfflineInterpreter  # local import avoids a cycle

    first_ids = OfflineInterpreter().match_facets(state.target, texts[0]) or turns[0].facets_covered
    first_kinds = [state.target.facet(fid).kind.value for fid in first_ids if state.target.facet(fid)]
    app_total = sum(f.appearance for f in feats)
    if first_kinds:
        if first_kinds[0] in ("function", "context") and "appearance" not in first_kinds[:1]:
            out.append((3, Observation(
                text="You tend to explain objects through what they do before what they look like.",
                evidence=f"Your first message started with {_kind_word(first_kinds[0])} and only later got to shape.")))
        elif first_kinds[0] == "appearance":
            out.append((3, Observation(
                text="You start with how things look, then work toward what they are for.",
                evidence="Your first message described its physical form before its purpose.")))
    if app_total == 0:
        out.append((2, Observation(
            text="You rarely describe physical shape unless asked.",
            evidence="No words about size, material, colour or form in any message.")))

    # 2. Metaphor habits
    sources = []
    for t in texts:
        sources += re.findall(r"\blike (?:a|an|your|the) ([a-z]+(?: [a-z]+)?)", t.lower())
    n_met = sum(len(f.metaphors) for f in feats)
    if n_met >= 2:
        ex = ", ".join(f"'{s}'" for s in sources[:3]) if sources else ""
        out.append((4, Observation(
            text="You frequently explain the unfamiliar by comparing it to something familiar.",
            evidence=(f"You reached for {ex}." if ex else f"{n_met} comparisons across the round."))))
    elif n_met == 0:
        out.append((2, Observation(
            text="You describe things literally, almost like a technical manual.",
            evidence="Not a single 'like a…' or 'imagine…' in the whole round.")))

    # 3. Perspective
    outsider = sum(f.outsider for f in feats)
    insider = sum(f.insider for f in feats)
    if outsider >= 2 and outsider > insider:
        out.append((3, Observation(
            text="You naturally step outside your own species to explain it.",
            evidence=f"You referred to 'humans' or similar {outsider} times, as if you were not one.")))
    elif insider >= 2:
        out.append((2, Observation(
            text="You explain from the inside, as a member of the species.",
            evidence=f"'We' and 'our' appeared {insider} times. The alien felt invited into a club.")))

    # 4. Following the alien's questions
    answered = asked = 0
    for i, m in enumerate(state.messages):
        if m.role == "alien" and m.metrics is None and any(l.endswith("?") for l in m.lines):
            nxt = next((x for x in state.messages[i + 1 :] if x.role == "player"), None)
            if nxt:
                asked += 1
                if nxt.facets_covered:
                    answered += 1
    if asked >= 2:
        if answered / asked >= 0.6:
            out.append((2, Observation(
                text="When the alien was confused, you answered its question directly.",
                evidence=f"You responded to {answered} of {asked} questions with new information.")))
        else:
            out.append((2, Observation(
                text="You tend to follow your own line of explanation rather than the listener's questions.",
                evidence=f"Only {answered} of {asked} alien questions got a direct answer.")))

    # 5. Pace
    avg_words = mean(f.n for f in feats)
    if len(turns) >= 3 and avg_words < 14:
        out.append((1, Observation(
            text="You explain in short bursts and let the listener catch up.",
            evidence=f"{len(turns)} messages, about {round(avg_words)} words each.")))
    elif avg_words > 45:
        out.append((1, Observation(
            text="You prefer to send everything at once.",
            evidence=f"Your messages averaged {round(avg_words)} words.")))

    # 6. Systems thinking, tied back to their board
    mech = sum(f.mechanism for f in feats)
    themes = (state.personalization.themes if state.personalization else [])
    if mech >= 3:
        tie = f" Someone who saves {themes[0].lower()} images might not be surprised." if themes else ""
        out.append((2, Observation(
            text="You tend to solve unfamiliar problems by explaining how the parts work.",
            evidence=f"You used mechanism words (push, turn, slide…) {mech} times.{tie}")))

    out.sort(key=lambda x: -x[0])
    return [o for _, o in out[:3]]


def _kind_word(kind: str) -> str:
    return {"function": "its purpose", "context": "where it is used", "mechanism": "how it works", "appearance": "its shape"}[kind]


def verdict(state: GameState) -> list[str]:
    v = Voice(state.personality, state.game_id + "verdict")
    if state.status == GameStatus.success:
        opener = "Your explanation was excellent." if (state.score and state.score.final >= 80) else "Your explanation was acceptable."
        return [opener, f"You described {state.target.alien_summary}.", v.pick("closing")]
    guess = state.hypothesis.text.rstrip(".")
    guess = guess[0].lower() + guess[1:] if guess else "nothing"
    return [
        "Time is up." if state.status == GameStatus.timeout else "Transmission ended.",
        f"My best understanding: {guess}.",
        f"Apparently it was a {state.target.name}.",
        v.pick("fail_closing"),
    ]
