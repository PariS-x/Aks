"""AKS API.

    /api/health
    /api/games                                      list registered creativity games
    /api/profile/demo-boards                        sample boards (demo mode)
    /api/profile/demo/{board_id}                    analyze a sample board
    /api/profile/analyze      {board_url}           analyze a public Pinterest board
    /api/profile              {VisualProfile}       hand-off from the full AKS pipeline

    /api/games/alien-explanation/sessions                    create a round
    /api/games/alien-explanation/sessions/{id}               current public state
    /api/games/alien-explanation/sessions/{id}/start         start the clock
    /api/games/alien-explanation/sessions/{id}/check         live forbidden-word check (no state change)
    /api/games/alien-explanation/sessions/{id}/messages      transmit an explanation
    /api/games/alien-explanation/sessions/{id}/tick          let the server expire the timer
    /api/games/alien-explanation/sessions/{id}/give-up
    /api/games/alien-explanation/sessions/{id}/result        final score + reflection
    /api/games/alien-explanation/sessions/{id}/next          next specimen, same player
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .core.game import GameRegistry, PlayerInput, StartOptions
from .core.store import MemoryStore
from .games.alien_explanation.engine import AlienExplanationGame, InputRejected
from .games.alien_explanation.models import GameState, Violation
from .games.alien_explanation.voice import PERSONALITIES
from .llm.client import get_client
from .profile.analyzer import analyze_pins, analyze_with_llm
from .profile.demo_boards import demo_profile, list_demo_boards, DEMO_BOARDS
from .profile.models import VisualProfile
from .profile.pinterest import PinterestError, fetch_board

logging.basicConfig(level=logging.INFO)

llm = get_client()
registry = GameRegistry()
alien = AlienExplanationGame(llm=llm, generate_objects=os.getenv("AKS_GENERATE_OBJECTS") == "1")
registry.register(alien)
sessions: MemoryStore[GameState] = MemoryStore()

app = FastAPI(title="AKS", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("AKS_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/games/alien-explanation/sessions"


# ---------------------------------------------------------------- meta


@app.get("/api/health")
async def health():
    return {"ok": True, "alien_mode": alien.mode, "personalities": {k: {"label": v["label"], "blurb": v["blurb"]} for k, v in PERSONALITIES.items()}}


@app.get("/api/games")
async def games():
    return registry.list()


# ---------------------------------------------------------------- profile


class AnalyzeRequest(BaseModel):
    board_url: str = Field(min_length=5, max_length=400)


@app.get("/api/profile/demo-boards")
async def demo_boards():
    return list_demo_boards()


@app.get("/api/profile/demo/{board_id}", response_model=VisualProfile)
async def demo(board_id: str):
    if board_id not in DEMO_BOARDS:
        raise HTTPException(404, "Unknown demo board")
    return demo_profile(board_id)


@app.post("/api/profile/analyze", response_model=VisualProfile)
async def analyze(req: AnalyzeRequest):
    try:
        title, pins, url = await fetch_board(req.board_url)
    except PinterestError as e:
        raise HTTPException(422, str(e))
    profile = analyze_pins(pins, board_name=title, source="pinterest", board_url=url)
    if llm:
        profile = await analyze_with_llm(llm, pins, profile)
    else:
        profile.analysis_note = "No image model connected, so AKS only read the pin text. Set GEMINI_API_KEY (free) to let it see the images."
    return profile


@app.post("/api/profile", response_model=VisualProfile)
async def accept_profile(profile: VisualProfile):
    """For the full AKS pipeline: hand over an already-analysed profile."""
    return profile


# ---------------------------------------------------------------- game


class CreateSession(BaseModel):
    profile: Optional[VisualProfile] = None
    demo_board_id: Optional[str] = None
    difficulty: Optional[int] = Field(None, ge=1, le=3)
    duration_s: int = Field(90, ge=30, le=300)
    personality: str = "archivist"


class TextIn(BaseModel):
    text: str = Field(max_length=2000)
    player_id: str = "p1"


async def _load(gid: str) -> GameState:
    s = await sessions.get(gid)
    if not s:
        raise HTTPException(404, "Session not found or expired")
    return s


@app.post(PREFIX)
async def create(req: CreateSession):
    profile = req.profile
    if not profile and req.demo_board_id:
        if req.demo_board_id not in DEMO_BOARDS:
            raise HTTPException(404, "Unknown demo board")
        profile = demo_profile(req.demo_board_id)
    personality = req.personality if req.personality in PERSONALITIES else "archivist"
    state = await alien.start(StartOptions(profile=profile, difficulty=req.difficulty, duration_s=req.duration_s, personality=personality))
    await sessions.put(state.game_id, state)
    return alien.public_view(state)


@app.get(PREFIX + "/{gid}")
async def get_state(gid: str):
    s = await _load(gid)
    async with sessions.lock(gid):
        s = alien.expire_if_due(s)
        await sessions.put(gid, s)
    return alien.public_view(s)


@app.post(PREFIX + "/{gid}/start")
async def start(gid: str):
    async with sessions.lock(gid):
        s = alien.begin(await _load(gid))
        await sessions.put(gid, s)
    return alien.public_view(s)


@app.post(PREFIX + "/{gid}/check", response_model=list[Violation])
async def check(gid: str, body: TextIn):
    s = await _load(gid)
    return alien.check(s, body.text)


@app.post(PREFIX + "/{gid}/messages")
async def message(gid: str, body: TextIn):
    async with sessions.lock(gid):
        s = await _load(gid)
        try:
            s = await alien.process_input(s, PlayerInput(text=body.text, player_id=body.player_id))
        except InputRejected as e:
            raise HTTPException(409, str(e))
        await sessions.put(gid, s)
    return alien.public_view(s)


@app.post(PREFIX + "/{gid}/tick")
async def tick(gid: str):
    async with sessions.lock(gid):
        s = alien.expire_if_due(await _load(gid))
        await sessions.put(gid, s)
    return alien.public_view(s)


@app.post(PREFIX + "/{gid}/give-up")
async def give_up(gid: str):
    async with sessions.lock(gid):
        s = alien.give_up(await _load(gid))
        await sessions.put(gid, s)
    return alien.public_view(s)


@app.get(PREFIX + "/{gid}/result")
async def result(gid: str):
    s = await _load(gid)
    try:
        return alien.evaluate(s)
    except InputRejected as e:
        raise HTTPException(409, str(e))


@app.post(PREFIX + "/{gid}/next")
async def next_round(gid: str):
    prev = await _load(gid)
    exclude = prev.played + [prev.target.id]
    state = await alien.start(StartOptions(profile=prev.profile, duration_s=prev.duration_s, personality=prev.personality, exclude=exclude))
    state.round_number = prev.round_number + 1
    await sessions.put(state.game_id, state)
    return alien.public_view(state)
