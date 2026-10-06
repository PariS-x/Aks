import asyncio
import json
import time

import pytest
from fastapi.testclient import TestClient

from app.core.game import PlayerInput, StartOptions
from app.games.alien_explanation import catalog
from app.games.alien_explanation.constraints import ConstraintChecker, redact_name, visible_forbidden
from app.games.alien_explanation.engine import AlienExplanationGame, InputRejected
from app.games.alien_explanation.models import GameStatus
from app.games.alien_explanation.personalization import select_object
from app.profile.analyzer import analyze_pins
from app.profile.demo_boards import DEMO_BOARDS, demo_profile
from app.profile.models import Pin
from app.profile.pinterest import PinterestError, parse_board_url, parse_rss


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------- constraints


@pytest.mark.parametrize(
    "text,expected",
    [
        ("You use this to clean your teeth.", ["teeth"]),
        ("It is moral, choral and floral.", []),  # no substring false positives
        ("A tiny broom for the face.", []),
        ("brushing", ["brushing"]),
        ("t00thbrush", ["t00thbrush"]),
        ("t o o t h", ["t o o t h"]),
        ("tooth-brush", ["tooth-brush"]),
        ("Toothbrushes", ["Toothbrushes"]),
    ],
)
def test_toothbrush_constraints(text, expected):
    got = [v.matched for v in ConstraintChecker(catalog.get("toothbrush")).check(text)]
    assert got == expected


def test_multiword_and_joined_names():
    c = ConstraintChecker(catalog.get("seatbelt"))
    assert [v.tier for v in c.check("seat-belt")] == ["name"]
    assert [v.tier for v in c.check("the seat belt")] == ["name"]
    c = ConstraintChecker(catalog.get("traffic_light"))
    assert [v.tier for v in c.check("trafficlight")] == ["name"]


def test_allowed_lookalike():
    c = ConstraintChecker(catalog.get("fork"))
    assert [v.matched for v in c.check("a forklift and forks")] == ["forks"]


def test_spans_point_at_text():
    text = "Clean your teeth with it."
    v = ConstraintChecker(catalog.get("toothbrush")).check(text)[0]
    assert text[v.start : v.end] == "teeth"


def test_name_hidden_from_forbidden_list():
    shown = visible_forbidden(catalog.get("toothbrush"))
    assert shown[0] == "ITS HUMAN NAME" and "TOOTHBRUSH" not in shown and "BRISTLE" in shown
    assert visible_forbidden(catalog.get("traffic_light")) == ["ITS HUMAN NAME", "TRAFFIC"]


def test_redaction():
    assert "toothbrush" not in redact_name("Is it a Toothbrush?", catalog.get("toothbrush")).lower()


def test_catalog_integrity():
    for o in catalog.CATALOG:
        assert o.forbidden_terms[0].tier == "name" and not o.forbidden_terms[0].visible
        assert any(f.core for f in o.facets)
        for c in o.combos:
            assert all(o.facet(r) for r in c.requires), (o.id, c.requires)
        assert o.image_url.startswith("/objects/s")


# ---------------------------------------------------------------- engine


def new_game(obj="toothbrush", llm=None, duration=90):
    g = AlienExplanationGame(llm=llm)
    s = run(g.start(StartOptions(duration_s=duration)))
    s.target = catalog.get(obj)
    return g, g.begin(s)


def test_full_offline_round_succeeds():
    g, s = new_game()
    for t in [
        "Humans hold a small plastic stick in their hand.",
        "One end is covered in tiny stiff hairs, like a miniature broom.",
        "They put it inside their mouth every morning and scrub away food, with a minty paste.",
    ]:
        s = run(g.process_input(s, PlayerInput(text=t)))
    assert s.status == GameStatus.success
    assert s.understanding >= 0.8
    assert len(s.hypothesis_trail) == 3
    assert [h.confidence for h in s.hypothesis_trail] == sorted(h.confidence for h in s.hypothesis_trail)
    r = g.evaluate(s)
    assert r.score.final > 0 and len(r.score.lines) == 6
    assert any("broom" in l for l in r.verdict)
    assert r.observations


def test_understanding_capped_without_core_facets():
    g, s = new_game()
    s = run(g.process_input(s, PlayerInput(text="Small plastic stick you hold in your hand, made of plastic, like a wand.")))
    assert s.status == GameStatus.playing and s.understanding <= 0.79


def test_violation_recorded_and_alien_horrified():
    g, s = new_game()
    s = run(g.process_input(s, PlayerInput(text="You clean your teeth with it.")))
    assert len(s.violations) == 1
    alien = s.messages[-1]
    assert alien.mood.value == "horrified"
    assert any("FORBIDDEN" in l.upper() for l in alien.lines)


def test_alien_never_leaks_name_before_success():
    class Leaky:
        name = "fake"

        async def complete(self, system, user, max_tokens=800):
            return json.dumps({
                "understanding": 0.3, "clarity": 0.5, "originality": 0.5, "defamiliarization": 0.5, "metaphor": 0,
                "facets_covered": ["handheld"], "hypothesis": "maybe a toothbrush", "known_properties": [],
                "remaining_questions": [], "alien_response": ["Is it a toothbrush?"], "guessed_object": None,
                "mood": "thinking", "should_continue": True,
            })

    g, s = new_game(llm=Leaky())
    s = run(g.process_input(s, PlayerInput(text="You hold it.")))
    said = " ".join(s.messages[-1].lines).lower() + s.hypothesis.text.lower()
    assert "toothbrush" not in said
    assert s.interpreter_used == ["llm"]


def test_llm_garbage_falls_back_to_offline():
    class Broken:
        name = "fake"

        async def complete(self, system, user, max_tokens=800):
            return "I am an alien and I refuse to produce JSON."

    g, s = new_game(llm=Broken())
    s = run(g.process_input(s, PlayerInput(text="Humans hold it in their hand.")))
    assert s.interpreter_used == ["offline"]
    assert s.messages[-1].lines


def test_llm_cannot_jump_to_victory():
    class Overconfident:
        name = "fake"

        async def complete(self, system, user, max_tokens=800):
            return json.dumps({
                "understanding": 1.0, "clarity": 1, "originality": 1, "defamiliarization": 1, "metaphor": 1,
                "facets_covered": ["bogus", "handheld"], "hypothesis": "x", "alien_response": ["I KNOW WHAT THIS IS."],
                "guessed_object": "toothbrush", "mood": "victory", "should_continue": False,
            })

    g, s = new_game(llm=Overconfident())
    s = run(g.process_input(s, PlayerInput(text="It is a thing.")))
    assert s.status == GameStatus.playing  # core facets not covered
    assert s.understanding <= 0.79
    assert "bogus" not in s.covered_facets


def test_timeout_is_server_owned():
    g, s = new_game(duration=30)
    s.started_at = time.time() - 40
    s = run(g.process_input(s, PlayerInput(text="too late")))
    assert s.status == GameStatus.timeout and s.score is not None
    with pytest.raises(InputRejected):
        run(g.process_input(s, PlayerInput(text="more")))


def test_empty_input_rejected():
    g, s = new_game()
    with pytest.raises(InputRejected):
        run(g.process_input(s, PlayerInput(text="   ")))


# ---------------------------------------------------------------- profile


def test_demo_boards_produce_themes():
    for bid in DEMO_BOARDS:
        p = demo_profile(bid)
        assert len(p.themes) >= 3 and p.reflection


def test_personalization_prefers_related_objects():
    p = demo_profile("orbit-and-concrete")
    picks = {select_object(p, seed=str(i))[0].id for i in range(40)}
    space_arch = {"telescope", "satellite_dish", "elevator", "traffic_light", "seatbelt", "screwdriver", "doorbell", "vending_machine", "passport", "remote_control"}
    assert picks and picks <= space_arch | {"umbrella", "zipper", "headphones", "shopping_cart", "fork", "toothbrush"}
    assert len(picks & space_arch) >= len(picks) * 0.7


def test_analyzer_short_keywords_are_whole_words():
    p = analyze_pins([Pin(title="Cardigan knit outfit"), Pin(title="Knitted cardigan, vintage style")])
    assert "cars" not in {t.name for t in p.themes}
    assert "fashion" in {t.name for t in p.themes}


def test_pinterest_url_parsing_and_rss():
    assert parse_board_url("https://www.pinterest.com/ari/orbit-and-concrete/") == ("ari", "orbit-and-concrete")
    with pytest.raises(PinterestError):
        parse_board_url("https://example.com/x/y")
    rss = """<?xml version="1.0"?><rss><channel><title>orbit</title>
      <item><title>Mars rover wheel</title><link>https://p/1</link>
      <description>&lt;img src="https://i.pinimg.com/a.jpg"&gt; close up of a rover</description></item>
    </channel></rss>"""
    title, pins = parse_rss(rss)
    assert title == "orbit" and pins[0].image_url == "https://i.pinimg.com/a.jpg"
    assert "rover" in pins[0].description


# ---------------------------------------------------------------- API


def test_api_flow():
    from app.main import app

    c = TestClient(app)
    assert c.get("/api/health").json()["ok"]
    boards = c.get("/api/profile/demo-boards").json()
    s = c.post("/api/games/alien-explanation/sessions", json={"demo_board_id": boards[0]["id"]}).json()
    gid = s["game_id"]
    assert s["status"] == "intro" and s["revealed_name"] is None
    assert s["personalization"]["themes"]
    s = c.post(f"/api/games/alien-explanation/sessions/{gid}/start").json()
    assert s["status"] == "playing"
    v = c.post(f"/api/games/alien-explanation/sessions/{gid}/check", json={"text": "hello"}).json()
    assert v == []
    s = c.post(f"/api/games/alien-explanation/sessions/{gid}/messages", json={"text": "Humans use it every day."}).json()
    assert s["messages"][-1]["role"] == "alien"
    assert c.get(f"/api/games/alien-explanation/sessions/{gid}/result").status_code == 409
    s = c.post(f"/api/games/alien-explanation/sessions/{gid}/give-up").json()
    assert s["status"] == "failed" and s["revealed_name"]
    r = c.get(f"/api/games/alien-explanation/sessions/{gid}/result").json()
    assert r["score"]["title"]
    n = c.post(f"/api/games/alien-explanation/sessions/{gid}/next").json()
    assert n["round_number"] == 2 and n["object"]["specimen_number"] == 2


def test_quote_board_is_never_empty():
    pins = [Pin(title="", description="", image_url="https://i.pinimg.com/x.jpg") for _ in range(10)]
    p = analyze_pins(pins, board_name="deep thoughts", source="pinterest")
    assert p.themes and p.themes[0].name == "philosophy"
    assert any("little text" in line for line in p.reflection)
    assert analyze_pins([Pin()] * 3).reflection  # nothing at all still says something
