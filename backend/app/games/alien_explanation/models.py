"""Domain models for Alien Explanation.

The engine owns every one of these. The LLM is only ever asked to fill an
`Interpretation`, which is validated here before the engine accepts it.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from ...profile.models import VisualProfile


# ---------------------------------------------------------------------------
# Target object
# ---------------------------------------------------------------------------


class FacetKind(str, Enum):
    appearance = "appearance"
    function = "function"
    mechanism = "mechanism"
    context = "context"


class Facet(BaseModel):
    """One thing the alien needs to learn about the object.

    Facets are the ground truth for comprehension. Both interpreters (LLM and
    offline) report which facets an explanation covered; the engine turns
    coverage into understanding.
    """

    id: str
    kind: FacetKind
    property: str  # how the alien files it: "handheld", "used inside the mouth"
    fragment: str  # phrase used to compose the alien's hypothesis
    cues: list[str] = Field(default_factory=list)  # regexes (offline interpreter)
    take: str = ""  # alien's literal reading when it first learns this facet
    question: str = ""  # what the alien asks when this is still missing
    weight: float = 1.0
    core: bool = False  # must be covered before the alien may "understand"


class Combo(BaseModel):
    """A line the alien says once a specific set of facets is known."""

    requires: list[str]
    line: str


class ForbiddenTerm(BaseModel):
    term: str
    tier: Literal["name", "revealing"]
    # Shown to the player? The name itself is replaced by "ITS HUMAN NAME".
    visible: bool = True


class TargetObject(BaseModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    image_url: str = ""
    description: str  # visual description
    function: str
    forbidden_terms: list[ForbiddenTerm]
    allowed_lookalikes: list[str] = Field(default_factory=list)
    related_concepts: list[str] = Field(default_factory=list)
    conventional_words: list[str] = Field(default_factory=list)
    difficulty: int = Field(2, ge=1, le=3)
    personalization_tags: list[str] = Field(default_factory=list)
    facets: list[Facet]
    combos: list[Combo] = Field(default_factory=list)
    alien_summary: str  # "a tiny broom used to polish the bones inside your face"
    generated: bool = False

    @field_validator("facets")
    @classmethod
    def _needs_core(cls, v: list[Facet]) -> list[Facet]:
        if not v:
            raise ValueError("object needs facets")
        if not any(f.core for f in v):
            v[0].core = True
        return v

    def facet(self, fid: str) -> Optional[Facet]:
        return next((f for f in self.facets if f.id == fid), None)


class PublicObject(BaseModel):
    """What the player's client may see during play. No name, no facets."""

    id: str
    image_url: str
    specimen_number: int
    difficulty: int
    forbidden_display: list[str]
    generated: bool = False
    # Only for generated objects without an image: the human needs some way to
    # know what they are explaining. Rendered as a "for human eyes only" card.
    human_only_label: Optional[str] = None


# ---------------------------------------------------------------------------
# Conversation and state
# ---------------------------------------------------------------------------


class Violation(BaseModel):
    term: str  # the matched forbidden term (canonical)
    matched: str  # what the player actually typed
    start: int
    end: int
    tier: Literal["name", "revealing"]
    evasion: bool = False  # e.g. "t00th"


class Mood(str, Enum):
    curious = "curious"
    confused = "confused"
    suspicious = "suspicious"
    horrified = "horrified"
    impressed = "impressed"
    thinking = "thinking"
    victory = "victory"


class AlienHypothesis(BaseModel):
    text: str = "Unknown. Possibly food. Possibly a weapon."
    confidence: float = 0.0
    known_properties: list[str] = Field(default_factory=list)
    unknown_properties: list[str] = Field(default_factory=list)


class TurnMetrics(BaseModel):
    clarity: float = 0.0
    originality: float = 0.0
    defamiliarization: float = 0.0
    metaphor: float = 0.0
    redundancy: float = 0.0
    coverage_gain: float = 0.0


class Message(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:10])
    role: Literal["alien", "player", "system"]
    player_id: Optional[str] = None
    lines: list[str]  # alien speaks in beats; player text is a single line
    mood: Optional[Mood] = None
    violations: list[Violation] = Field(default_factory=list)
    metrics: Optional[TurnMetrics] = None
    facets_covered: list[str] = Field(default_factory=list)
    at: float = Field(default_factory=time.time)


class Player(BaseModel):
    id: str
    name: str = "Earth organism"


class GameStatus(str, Enum):
    intro = "intro"
    playing = "playing"
    success = "success"
    failed = "failed"
    timeout = "timeout"


class ScoreLine(BaseModel):
    key: str
    label: str
    value: int
    evidence: str  # why this number, in plain words


class GameScore(BaseModel):
    lines: list[ScoreLine]
    final: int
    title: str
    title_reason: str


class Observation(BaseModel):
    text: str
    evidence: str


class Personalization(BaseModel):
    themes: list[str]
    reason: str  # the alien's line on why it chose this object
    source: Literal["demo", "pinterest", "manual", "none"] = "none"


class GameState(BaseModel):
    game_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    game_type: str = "alien-explanation"
    round_number: int = 1
    specimen_number: int = 1
    players: list[Player] = Field(default_factory=lambda: [Player(id="p1")])
    target: TargetObject
    messages: list[Message] = Field(default_factory=list)
    hypothesis: AlienHypothesis = Field(default_factory=AlienHypothesis)
    hypothesis_trail: list[AlienHypothesis] = Field(default_factory=list)
    understanding: float = 0.0
    covered_facets: list[str] = Field(default_factory=list)
    violations: list[Violation] = Field(default_factory=list)
    duration_s: int = 90
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    status: GameStatus = GameStatus.intro
    personality: str = "archivist"
    personalization: Optional[Personalization] = None
    profile: Optional[VisualProfile] = None  # kept server-side for the next round
    played: list[str] = Field(default_factory=list)  # object ids already used in this sitting
    score: Optional[GameScore] = None
    observations: list[Observation] = Field(default_factory=list)
    interpreter_used: list[str] = Field(default_factory=list)
    last_question_facet: Optional[str] = None

    def time_remaining(self, now: Optional[float] = None) -> float:
        if self.started_at is None:
            return float(self.duration_s)
        end = self.ended_at or (now or time.time())
        return max(0.0, self.duration_s - (end - self.started_at))

    def player_turns(self) -> list[Message]:
        return [m for m in self.messages if m.role == "player"]


# ---------------------------------------------------------------------------
# Interpreter contract (validated LLM output)
# ---------------------------------------------------------------------------


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


class Interpretation(BaseModel):
    """What an interpreter returns for one player turn.

    This mirrors the JSON contract the LLM must produce. Anything outside the
    contract is rejected; numbers are clamped; unknown facet ids are dropped by
    the engine.
    """

    understanding: float
    clarity: float
    originality: float
    defamiliarization: float
    metaphor: float
    facets_covered: list[str] = Field(default_factory=list)
    hypothesis: str = Field(max_length=240)
    known_properties: list[str] = Field(default_factory=list, max_length=12)
    remaining_questions: list[str] = Field(default_factory=list, max_length=4)
    alien_response: list[str] = Field(min_length=1, max_length=5)
    guessed_object: Optional[str] = None
    mood: Mood = Mood.thinking
    should_continue: bool = True

    @field_validator("understanding", "clarity", "originality", "defamiliarization", "metaphor")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return _clamp01(v)

    @field_validator("alien_response")
    @classmethod
    def _short_lines(cls, v: list[str]) -> list[str]:
        out = [s.strip()[:220] for s in v if s and s.strip()]
        if not out:
            raise ValueError("alien said nothing")
        return out


# ---------------------------------------------------------------------------
# API views
# ---------------------------------------------------------------------------


class PublicState(BaseModel):
    game_id: str
    game_type: str
    status: GameStatus
    round_number: int
    object: PublicObject
    messages: list[Message]
    hypothesis: AlienHypothesis
    understanding: int  # 0-100
    violations_count: int
    words_used: int
    time_remaining: float
    duration_s: int
    personality: str
    personalization: Optional[Personalization] = None
    # Revealed only once the round is over
    revealed_name: Optional[str] = None
    alien_summary: Optional[str] = None


class GameResult(BaseModel):
    game_id: str
    status: GameStatus
    object_name: str
    alien_summary: str
    verdict: list[str]
    score: GameScore
    observations: list[Observation]
    turns: int
    seconds_used: int
    hypothesis_trail: list[AlienHypothesis]
