"""Theme extraction from pins.

Three layers, each optional on top of the last:

1. Keyword taxonomy over the board title, pin titles and descriptions.
   Transparent: every theme carries the pins that triggered it.
2. Fallback: if nothing matches (common for quote boards, where the words
   live inside the images), use the board title and the most repeated words,
   so the profile is never empty.
3. Vision (when an LLM key is set): look at the pin images themselves and
   re-rank the themes. This is what reads text-in-image pins properly.

The full multimodal AKS pipeline can skip all of this and POST a
VisualProfile to /api/profile.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict

from ..llm.client import LLMClient
from .models import Pin, Theme, VisualProfile

TAXONOMY: dict[str, list[str]] = {
    "space": ["space", "nasa", "planet", "galaxy", "nebula", "astronaut", "rocket", "orbit", "moon", "mars", "cosmos", "star", "stars", "telescope", "satellite", "rover", "astro", "universe"],
    "architecture": ["architecture", "brutalis", "concrete", "building", "facade", "tower", "staircase", "bauhaus", "modernis", "skyscraper", "structure", "pavilion"],
    "robotics": ["robot", "robotic", "mechatronic", "servo", "arduino", "actuator", "android", "automaton", "drone", "cyborg", "machine", "gripper"],
    "travel": ["travel", "trip", "wanderlust", "passport", "airport", "journey", "road trip", "backpack", "destination", "train", "station", "map"],
    "fashion": ["fashion", "outfit", "style", "streetwear", "vintage", "jacket", "dress", "sneaker", "runway", "denim", "knit", "wardrobe"],
    "food": ["food", "recipe", "bake", "bread", "coffee", "kitchen", "dinner", "pasta", "matcha", "dessert", "brunch", "cafe", "noodle"],
    "music": ["music", "vinyl", "record", "guitar", "synth", "concert", "band", "playlist", "headphone", "studio", "jazz", "song", "lyrics"],
    "nature": ["nature", "forest", "mountain", "ocean", "botanical", "plant", "flower", "moss", "garden", "hike", "lake", "fern", "sea", "sky"],
    "interiors": ["interior", "room", "apartment", "decor", "living room", "bedroom", "furniture", "lamp", "shelf", "home", "cozy", "chair"],
    "art": ["art", "painting", "illustration", "sketch", "collage", "gallery", "zine", "poster", "typography", "print", "drawing"],
    "tech": ["tech", "computer", "keyboard", "gadget", "retro tech", "circuit", "code", "setup", "desk setup", "screen", "camera", "electronics"],
    "cars": ["car", "cars", "porsche", "motor", "vintage car", "racing", "garage", "engine", "drive"],
    "cities": ["city", "street", "tokyo", "new york", "neon", "urban", "subway", "metro", "alley", "mumbai", "london"],
    "photography": ["photography", "film photo", "35mm", "analog", "polaroid", "portrait", "lens", "darkroom"],
    "wellness": ["wellness", "skincare", "yoga", "self care", "routine", "spa", "bath", "morning routine", "meditation", "healing"],
    "diy": ["diy", "craft", "handmade", "woodwork", "tools", "workshop", "build", "repair", "maker"],
    "film": ["film", "cinema", "movie", "director", "scene", "still", "tv", "series", "anime"],
    # Text-heavy and inward-looking boards
    "words": ["quote", "quotes", "poem", "poetry", "poet", "words", "writing", "writer", "letter", "letters", "journal", "diary", "handwriting", "typewriter", "literature", "book", "books", "reading", "library", "novel", "text", "sentence", "prose"],
    "philosophy": ["thought", "thoughts", "philosophy", "philosopher", "meaning", "existential", "existence", "deep", "mind", "soul", "truth", "reflection", "wisdom", "think", "thinking", "consciousness", "life", "reality", "camus", "nietzsche", "kafka", "dostoevsky"],
    "melancholy": ["sad", "sadness", "lonely", "loneliness", "alone", "melancholy", "grief", "heartbreak", "tears", "cry", "void", "empty", "silence", "quiet", "failure", "lost", "dark", "pain", "hurt", "tired"],
    "love": ["love", "romance", "romantic", "heart", "couple", "kiss", "relationship", "crush", "longing", "miss you", "soulmate"],
}

LABELS = {k: k.upper() for k in TAXONOMY}
BOARD_TITLE_WEIGHT = 3  # the board's own name is a strong, deliberate signal

STOP = set(
    """the a an and or of to in on for with my your our is are was be it this that i you me we they he she
    not no so but at by from as all just more most very like what when how why who pin pins board pinterest
    image images photo photos idea ideas""".split()
)


def _kw(k: str) -> str:
    # Short keywords must be whole words ("car" should not match "cardigan");
    # longer ones may take suffixes ("brutalis" -> "brutalist").
    return rf"\b{re.escape(k)}s?\b" if len(k) <= 4 else rf"\b{re.escape(k)}"


def _text(p: Pin) -> str:
    return f"{p.title} {p.description}".strip()


def analyze_pins(pins: list[Pin], board_name: str = "", source: str = "manual", board_url: str | None = None) -> VisualProfile:
    hits: dict[str, list[str]] = defaultdict(list)
    score: Counter[str] = Counter()

    corpus = [(_text(p)[:80], _text(p).lower()) for p in pins]
    for label, text in corpus:
        for theme, kws in TAXONOMY.items():
            if text and any(re.search(_kw(k), text) for k in kws):
                score[theme] += 1
                if label and label not in hits[theme]:
                    hits[theme].append(label)
    if board_name:
        for theme, kws in TAXONOMY.items():
            if any(re.search(_kw(k), board_name.lower()) for k in kws):
                score[theme] += BOARD_TITLE_WEIGHT
                hits[theme].insert(0, f"board title: {board_name}")

    total = max(1, len(pins)) + BOARD_TITLE_WEIGHT
    themes = [
        Theme(name=t, label=LABELS[t], weight=round(min(1.0, n / total * 2.2), 3), evidence=hits[t][:4])
        for t, n in score.items()
    ]
    themes.sort(key=lambda t: -t.weight)
    quiet = not themes
    if quiet:
        themes = _fallback_themes(pins, board_name)

    profile = VisualProfile(
        source=source, board_name=board_name, board_url=board_url, pin_count=len(pins),
        themes=themes[:6], sample_pins=pins[:12],
    )
    profile.reflection = reflection_lines(profile, text_poor=quiet or _text_poor(pins))
    return profile


def _text_poor(pins: list[Pin]) -> bool:
    if not pins:
        return True
    return sum(1 for p in pins if len(_text(p).split()) >= 3) < len(pins) * 0.3


def _fallback_themes(pins: list[Pin], board_name: str) -> list[Theme]:
    """No keyword matched. Use the most repeated words, then the board title."""
    words = Counter()
    for p in pins:
        for w in re.findall(r"[a-z]{4,}", _text(p).lower()):
            if w not in STOP:
                words[w] += 1
    out = [
        Theme(name=w, label=w.upper(), weight=round(min(1.0, n / max(1, len(pins)) * 2), 3), evidence=[])
        for w, n in words.most_common(4) if n >= 2
    ]
    if not out and board_name:
        title_words = [w for w in re.findall(r"[a-z]{3,}", board_name.lower()) if w not in STOP]
        out = [Theme(name=w, label=w.upper(), weight=0.6, evidence=[f"board title: {board_name}"]) for w in title_words[:3]]
    return out


def reflection_lines(p: VisualProfile, text_poor: bool = False) -> list[str]:
    top = p.top_themes(3)
    if not top:
        return [
            "Your pins say almost nothing in words. The meaning is all in the images.",
            "AKS reads pictures properly when an image model is connected.",
        ]
    names = [t.name for t in top]
    joined = ", ".join(names[:-1]) + " and " + names[-1] if len(names) > 1 else names[0]
    lines = [f"Your archive keeps returning to {joined}."]
    pairs = {
        frozenset({"space", "architecture"}): "You save structures, both the kind people build and the kind gravity builds.",
        frozenset({"robotics", "space"}): "You collect machines that go where people cannot.",
        frozenset({"food", "interiors"}): "You save places to be, and things to have while you are there.",
        frozenset({"music", "cities"}): "Your images have a soundtrack and it plays at night.",
        frozenset({"nature", "photography"}): "You notice light before you notice objects.",
        frozenset({"fashion", "art"}): "You treat clothing as a canvas.",
        frozenset({"travel", "photography"}): "You save places as if you might need proof you were there.",
        frozenset({"words", "philosophy"}): "You save sentences, mostly the kind people underline at 2am.",
        frozenset({"philosophy", "melancholy"}): "You keep thoughts other people would rather not have.",
        frozenset({"words", "melancholy"}): "You collect the words people find when something hurts.",
        frozenset({"words", "love"}): "You save what people say when they mean it.",
    }
    for pair, line in pairs.items():
        if pair <= set(names):
            lines.append(line)
            break
    else:
        ev = len(top[0].evidence)
        lines.append(f"The strongest signal is {names[0]}" + (f": {ev} pins point there." if ev else "."))
    if text_poor:
        lines.append("Most of your pins carry little text, so AKS read what it could.")
    return lines


# ---------------------------------------------------------------------------
# LLM layers
# ---------------------------------------------------------------------------

log = logging.getLogger("aks.profile")

_KEYS = ", ".join(TAXONOMY)
_CONTRACT = f"""Return ONLY a JSON object:
{{
  "themes": [{{"name": one of [{_KEYS}], "weight": 0..1, "evidence": "which pins show it, a few concrete words"}}],
  "aesthetic": ["3-5 short phrases on the visual qualities: palette, light, texture, composition, typography"],
  "motifs": ["3-6 concrete things that recur across pins, e.g. 'handwritten text on paper', 'empty rooms', 'night windows'"],
  "contradiction": "one tension between things this person saves, one sentence, or null",
  "reflection": ["2-3 short, specific sentences about what this collection says about the person. Observant, warm, a little poetic. No clichés, no flattery, no therapy language."]
}}
3-5 themes. Be specific to these exact pins, not generic."""


def _merge(base: VisualProfile, data: dict, mode: str) -> VisualProfile:
    by = {t.name: t for t in base.themes}
    merged = []
    for t in (data.get("themes") or [])[:5]:
        name = t.get("name") if isinstance(t, dict) else None
        if name not in TAXONOMY:
            continue
        try:
            w = max(0.0, min(1.0, float(t.get("weight", 0.5))))
        except (TypeError, ValueError):
            w = 0.5
        ev = ([str(t["evidence"])[:90]] if t.get("evidence") else []) + (by[name].evidence if name in by else [])
        merged.append(Theme(name=name, label=LABELS[name], weight=w, evidence=ev[:4]))
    if not merged:
        raise ValueError("model returned no usable themes")
    base.themes = merged
    clean = lambda xs, n, k: [str(x).strip()[:k] for x in (xs or []) if str(x).strip()][:n]  # noqa: E731
    base.aesthetic = clean(data.get("aesthetic"), 5, 60)
    base.motifs = clean(data.get("motifs"), 6, 60)
    c = data.get("contradiction")
    base.contradiction = str(c).strip()[:200] if c and str(c).strip().lower() != "null" else None
    lines = data.get("reflection")
    if isinstance(lines, str):
        lines = [lines]
    lines = clean(lines, 3, 220)
    base.reflection = lines or reflection_lines(base)
    base.analysis = mode
    base.analysis_note = None
    return base


def _parse(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError(f"no JSON in model reply: {raw[:120]!r}")
    return json.loads(m.group(0))


async def analyze_with_llm(client: LLMClient, pins: list[Pin], base: VisualProfile) -> VisualProfile:
    """Look at the pin images first; fall back to the text; keep the keyword profile if both fail.

    Failures are logged and surfaced as `analysis_note` so it is obvious when
    the images were not actually read.
    """
    images = [p.image_url for p in pins if p.image_url][:20]
    errors: list[str] = []
    if images and hasattr(client, "complete_with_images"):
        try:
            system = (
                "You are AKS, a visual analyst. You are shown the images a person saved to one Pinterest board. "
                "Look closely: read any text inside the images (quotes, poems, handwriting) and treat it as content. "
                + _CONTRACT
            )
            raw = await client.complete_with_images(system, f"Board name: {base.board_name}. {len(images)} pins shown.", images, max_tokens=1200)
            return _merge(base, _parse(raw), "vision")
        except Exception as e:  # noqa: BLE001
            log.warning("Vision analysis failed: %s", e)
            errors.append(f"image reading failed ({str(e)[:140]})")
    try:
        text = "\n".join(f"- {_text(p)}"[:160] for p in pins[:60] if _text(p))
        system = "You are AKS, a visual analyst. You only have the titles/descriptions of a person's saved pins. " + _CONTRACT
        raw = await client.complete(system, f"Board name: {base.board_name}\n{text or '(no text on pins)'}", max_tokens=900)
        out = _merge(base, _parse(raw), "text-llm")
        out.analysis_note = errors[0] if errors else None
        return out
    except Exception as e:  # noqa: BLE001
        log.warning("Text analysis failed: %s", e)
        errors.append(f"text analysis failed ({str(e)[:140]})")
    base.analysis_note = "; ".join(errors)
    return base