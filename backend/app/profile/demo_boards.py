"""Sample boards so AKS can be demonstrated without Pinterest.

They run through the same analyzer as real boards, so demo mode exercises the
real pipeline end to end.
"""

from __future__ import annotations

from .analyzer import analyze_pins
from .models import Pin, VisualProfile

DEMO_BOARDS: dict[str, dict] = {
    "orbit-and-concrete": {
        "name": "orbit & concrete",
        "blurb": "Rovers, brutalist stairwells, mission patches.",
        "pins": [
            "Mars rover wheel tread close-up", "Brutalist concrete staircase, Mumbai", "NASA mission patch archive",
            "Robot arm gripper prototype", "Saturn rings, Cassini raw image", "Bauhaus building facade",
            "Night train station in Tokyo", "Astronaut glove, 1969", "Servo motor wiring diagram",
            "Concrete pavilion in fog", "Rocket launch long exposure", "Old airport departures board",
            "Lunar module engineering sketch", "Spiral staircase from above",
        ],
    },
    "soft-kitchen": {
        "name": "soft kitchen",
        "blurb": "Bread, ceramics, morning light on linen.",
        "pins": [
            "Sourdough crumb shot", "Handmade ceramic coffee cup", "Morning routine with matcha",
            "Linen curtains, living room light", "Pasta from scratch recipe", "Cozy apartment kitchen shelf",
            "Brunch table styling", "Bath tray and candles self care", "Vintage lamp on a side table",
            "Lemon olive oil cake recipe", "Small balcony herb garden", "Dinner party place setting",
        ],
    },
    "night-bus-records": {
        "name": "night bus records",
        "blurb": "Vinyl, neon streets, oversized jackets.",
        "pins": [
            "Vinyl record shop in London", "Neon alley at night, Tokyo", "Oversized vintage leather jacket",
            "Synth studio setup", "Subway platform at 2am", "Concert crowd film photo 35mm",
            "Streetwear outfit grid", "Headphones and cassette flatlay", "Anime city scene still",
            "Jazz club poster typography", "Denim on denim street style", "DJ booth from above",
        ],
    },
    "field-notes": {
        "name": "field notes",
        "blurb": "Moss, film cameras, trail maps, tools.",
        "pins": [
            "Moss macro photography", "Analog film camera collection", "Hand-drawn trail map",
            "Woodwork workshop tools wall", "Fern botanical illustration", "Mountain lake at dawn",
            "DIY bookshelf build", "Polaroid of a forest road", "Repair kit in a canvas roll",
            "Backpack packing list for a hike", "Garden shed workshop", "Ocean fog portrait",
        ],
    },
}


def demo_profile(board_id: str) -> VisualProfile:
    b = DEMO_BOARDS[board_id]
    pins = [Pin(title=t) for t in b["pins"]]
    return analyze_pins(pins, board_name=b["name"], source="demo")


def list_demo_boards() -> list[dict]:
    return [
        {"id": k, "name": v["name"], "blurb": v["blurb"], "pins": v["pins"][:6], "pin_count": len(v["pins"])}
        for k, v in DEMO_BOARDS.items()
    ]
