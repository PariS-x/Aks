"""The common contract every AKS creativity game implements.

Alien Explanation is the only game today. Future games add a package under
`app/games/<id>/` and register themselves; the API layer stays generic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel

from ..profile.models import VisualProfile


class StartOptions(BaseModel):
    profile: Optional[VisualProfile] = None
    difficulty: Optional[int] = None
    duration_s: int = 90
    personality: str = "archivist"
    exclude: list[str] = []
    players: list[str] = []  # multiplayer-ready: names of human players


class PlayerInput(BaseModel):
    text: str
    player_id: str = "p1"


class CreativityGame(ABC):
    id: str
    name: str
    description: str

    @abstractmethod
    async def start(self, options: StartOptions) -> Any:
        """Create a new game state (status: intro)."""

    @abstractmethod
    def begin(self, state: Any) -> Any:
        """Start the clock."""

    @abstractmethod
    async def process_input(self, state: Any, inp: PlayerInput) -> Any:
        """Apply one player input and return the next state."""

    @abstractmethod
    def evaluate(self, state: Any) -> Any:
        """Final result for a finished state."""

    @abstractmethod
    def public_view(self, state: Any) -> BaseModel:
        """What the client is allowed to see."""


class GameRegistry:
    def __init__(self) -> None:
        self._games: dict[str, CreativityGame] = {}

    def register(self, game: CreativityGame) -> None:
        self._games[game.id] = game

    def get(self, game_id: str) -> CreativityGame:
        return self._games[game_id]

    def list(self) -> list[dict]:
        return [{"id": g.id, "name": g.name, "description": g.description} for g in self._games.values()]
