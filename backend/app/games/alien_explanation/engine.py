"""The deterministic game engine.

    GameState -> ConstraintChecker -> Interpreter(s) -> blend & guard
              -> AlienHypothesis -> status/timer -> ScoreEngine -> GameState

The LLM interprets. The engine decides. In particular the engine alone owns:
the clock, forbidden-word detection, how far understanding may move in one
turn, whether the round is won, whether the alien may say the name, and every
score.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from ...core.game import CreativityGame, PlayerInput, StartOptions
from ...llm.client import LLMClient, LLMError
from . import catalog
from .constraints import ConstraintChecker, redact_name, visible_forbidden
from .features import extract
from .interpreter import LLMInterpreter, OfflineInterpreter, TurnContext, coverage_understanding
from .models import (
    AlienHypothesis, GameResult, GameState, GameStatus, Interpretation, Message, Mood,
    Player, PublicObject, PublicState, TurnMetrics,
)
from .personalization import generate_object, select_object
from .scoring import observations, score, verdict
from .voice import Voice

log = logging.getLogger("aks.alien")

MAX_TURNS = 12
MAX_CHARS = 600
GRACE_S = 2.5  # network latency allowance on the timer
MAX_GAIN_PER_TURN = 0.5
MAX_DROP_PER_TURN = 0.08


class InputRejected(Exception):
    pass


class AlienExplanationGame(CreativityGame):
    id = "alien-explanation"
    name = "Alien Explanation"
    description = "Explain a mundane Earth object to an extraterrestrial without using its name."

    def __init__(self, llm: Optional[LLMClient] = None, generate_objects: bool = False):
        self.llm = llm
        self.offline = OfflineInterpreter()
        self.llm_interp = LLMInterpreter(llm) if llm else None
        self.generate_objects = generate_objects and llm is not None

    @property
    def mode(self) -> str:
        return f"llm:{self.llm.name}" if self.llm else "offline"

    # ------------------------------------------------------------------ start

    async def start(self, options: StartOptions) -> GameState:
        target, pers = None, None
        if self.generate_objects and options.profile and options.profile.themes:
            target = await generate_object(self.llm, options.profile, options.exclude)
            if target:
                _, pers = select_object(options.profile, options.exclude)
        if target is None:
            target, pers = select_object(options.profile, options.exclude, options.difficulty)
        players = [Player(id=f"p{i + 1}", name=n) for i, n in enumerate(options.players)] or [Player(id="p1")]
        return GameState(
            target=target,
            personalization=pers,
            duration_s=max(30, min(300, options.duration_s)),
            personality=options.personality,
            players=players,
            specimen_number=len(options.exclude) + 1,
            profile=options.profile,
            played=list(options.exclude),
        )

    def begin(self, state: GameState) -> GameState:
        if state.status != GameStatus.intro:
            return state
        state.status = GameStatus.playing
        state.started_at = time.time()
        state.messages.append(
            Message(role="alien", lines=["I have no idea what this object does.", "Explain."], mood=Mood.curious)
        )
        return state

    # ------------------------------------------------------------------ turns

    def check(self, state: GameState, text: str):
        return ConstraintChecker(state.target).check(text[:MAX_CHARS])

    async def process_input(self, state: GameState, inp: PlayerInput) -> GameState:
        if state.status != GameStatus.playing:
            raise InputRejected("This round is not in progress.")
        if state.time_remaining() <= -GRACE_S or (state.started_at and time.time() - state.started_at > state.duration_s + GRACE_S):
            return self._finish(state, GameStatus.timeout)
        text = " ".join(inp.text.split())[:MAX_CHARS]
        if not text:
            raise InputRejected("Say something. The alien is waiting.")

        violations = ConstraintChecker(state.target).check(text)
        seed = f"{state.game_id}:{len(state.messages)}"
        ctx = TurnContext(
            target=state.target, history=state.messages, text=text, violations=violations,
            covered_before=list(state.covered_facets), hypothesis_before=state.hypothesis,
            understanding_before=state.understanding, personality=state.personality, seed=seed,
            last_question_facet=state.last_question_facet, time_remaining=state.time_remaining(),
        )

        offline = await self.offline.interpret(ctx)
        interp, used = offline, "offline"
        if self.llm_interp:
            try:
                llm_out = await self.llm_interp.interpret(ctx)
                interp, used = self._blend(state, llm_out, offline), "llm"
            except (LLMError, Exception) as e:  # never let the model break a round
                log.warning("LLM interpreter failed, using offline: %s", e)
        state.interpreter_used.append(used)

        # --- engine-owned decisions -------------------------------------
        before = set(state.covered_facets)
        after = before | set(interp.facets_covered)
        target_u = interp.understanding
        u = max(state.understanding - MAX_DROP_PER_TURN, min(state.understanding + MAX_GAIN_PER_TURN, target_u))
        cores = [f.id for f in state.target.facets if f.core]
        all_core = all(c in after for c in cores)
        if not all_core:
            u = min(u, 0.79)
        guessed_right = self._matches_name(state, interp.guessed_object)
        solved = all_core and (u >= 0.8 or (guessed_right and u >= 0.7))
        if solved:
            u = max(u, 0.9)

        lines = list(interp.alien_response)
        if violations and not any("FORBIDDEN" in l.upper() for l in lines):
            lines.insert(0, "FORBIDDEN HUMAN CONCEPT DETECTED.")
        if solved:
            lines = [l for l in lines if "KNOW WHAT THIS IS" not in l.upper()]
            lines += ["I KNOW WHAT THIS IS.", f"You are describing a {state.target.name}."]
        else:
            lines = [redact_name(l, state.target) for l in lines]
        mood = Mood.victory if solved else Mood.horrified if violations else interp.mood
        if mood == Mood.victory and not solved:
            mood = Mood.impressed

        tf = extract(text)
        prev_stems = [s for m in state.player_turns() for s in extract(" ".join(m.lines)).content_stems]
        redundancy = sum(1 for s in tf.content_stems if s in set(prev_stems)) / len(tf.content_stems) if tf.content_stems else 0.0

        player_msg = Message(
            role="player", player_id=inp.player_id, lines=[text], violations=violations,
            facets_covered=[f for f in interp.facets_covered if f not in before],
            metrics=TurnMetrics(
                clarity=interp.clarity, originality=interp.originality,
                defamiliarization=interp.defamiliarization, metaphor=interp.metaphor,
                redundancy=redundancy, coverage_gain=max(0.0, u - state.understanding),
            ),
        )
        state.messages += [player_msg, Message(role="alien", lines=lines[:6], mood=mood)]
        state.violations += violations
        state.covered_facets = [f.id for f in state.target.facets if f.id in after]
        state.understanding = round(u, 3)

        hyp_text = interp.hypothesis if solved else redact_name(interp.hypothesis, state.target)
        state.hypothesis = AlienHypothesis(
            text=hyp_text,
            confidence=state.understanding,
            known_properties=interp.known_properties or [state.target.facet(f).property for f in state.covered_facets],
            unknown_properties=interp.remaining_questions,
        )
        state.hypothesis_trail.append(state.hypothesis)
        state.last_question_facet = next(
            (f.id for f in state.target.facets if f.question and f.question in " ".join(lines)), state.last_question_facet
        )

        if solved:
            return self._finish(state, GameStatus.success)
        if len(state.player_turns()) >= MAX_TURNS:
            return self._finish(state, GameStatus.failed)
        return state

    def _blend(self, state: GameState, llm: Interpretation, offline: Interpretation) -> Interpretation:
        """Accept the model's voice; anchor its numbers to evidence."""
        facets = list(dict.fromkeys(llm.facets_covered + offline.facets_covered))
        cov_u = coverage_understanding(state.target, set(state.covered_facets) | set(facets))
        w = 0.6
        return llm.model_copy(update=dict(
            facets_covered=facets,
            understanding=0.5 * cov_u + 0.5 * llm.understanding,
            clarity=w * llm.clarity + (1 - w) * offline.clarity,
            originality=w * llm.originality + (1 - w) * offline.originality,
            defamiliarization=w * llm.defamiliarization + (1 - w) * offline.defamiliarization,
            metaphor=w * llm.metaphor + (1 - w) * offline.metaphor,
        ))

    def _matches_name(self, state: GameState, guess: Optional[str]) -> bool:
        if not guess:
            return False
        g = guess.lower().strip(" .!?\"'")
        g = g.removeprefix("a ").removeprefix("an ").removeprefix("the ")
        names = {state.target.name.lower(), *(a.lower() for a in state.target.aliases)}
        return any(g == n or g == n + "s" or n in g.split(" ") or g.replace(" ", "") == n.replace(" ", "") for n in names)

    # ------------------------------------------------------------------ end

    def expire_if_due(self, state: GameState) -> GameState:
        if state.status == GameStatus.playing and state.started_at and time.time() - state.started_at >= state.duration_s - 0.5:
            return self._finish(state, GameStatus.timeout)
        return state

    def give_up(self, state: GameState) -> GameState:
        if state.status == GameStatus.playing:
            return self._finish(state, GameStatus.failed)
        return state

    def _finish(self, state: GameState, status: GameStatus) -> GameState:
        state.status = status
        state.ended_at = time.time()
        if status != GameStatus.success:
            v = Voice(state.personality, state.game_id + "end")
            state.messages.append(Message(role="alien", lines=["Time is up." if status == GameStatus.timeout else "Very well.", v.pick("fail_closing")], mood=Mood.confused))
        state.score = score(state)
        state.observations = observations(state)
        return state

    def evaluate(self, state: GameState) -> GameResult:
        if state.status in (GameStatus.intro, GameStatus.playing):
            raise InputRejected("Round not finished.")
        return GameResult(
            game_id=state.game_id, status=state.status, object_name=state.target.name,
            alien_summary=state.target.alien_summary, verdict=verdict(state),
            score=state.score, observations=state.observations,
            turns=len(state.player_turns()),
            seconds_used=round(state.duration_s - state.time_remaining()),
            hypothesis_trail=state.hypothesis_trail,
        )

    # ------------------------------------------------------------------ view

    def public_view(self, state: GameState) -> PublicState:
        done = state.status not in (GameStatus.intro, GameStatus.playing)
        t = state.target
        return PublicState(
            game_id=state.game_id, game_type=self.id, status=state.status, round_number=state.round_number,
            object=PublicObject(
                id=f"specimen-{state.specimen_number:03d}", image_url=t.image_url,
                specimen_number=state.specimen_number, difficulty=t.difficulty,
                forbidden_display=visible_forbidden(t), generated=t.generated,
                human_only_label=t.name if t.generated and not t.image_url else None,
            ),
            messages=state.messages,
            hypothesis=state.hypothesis,
            understanding=round(state.understanding * 100),
            violations_count=len(state.violations),
            words_used=sum(len(" ".join(m.lines).split()) for m in state.player_turns()),
            time_remaining=round(state.time_remaining(), 1),
            duration_s=state.duration_s,
            personality=state.personality,
            personalization=state.personalization,
            revealed_name=t.name if done else None,
            alien_summary=t.alien_summary if done else None,
        )


def catalog_size() -> int:
    return len(catalog.CATALOG)
