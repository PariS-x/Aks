"""Cheap, deterministic text features.

Used three ways: by the offline interpreter, as a sanity anchor blended with
the LLM's judgement, and as evidence for the end-of-round observations.
Every feature here is something the UI can point at and explain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .constraints import stem

WORD = re.compile(r"[a-z']+")

METAPHOR_PATTERNS = [
    r"\blike an?\b", r"\blike (your|my|the|some)\b", r"\bas if\b", r"\bas though\b", r"\bimagine\b",
    r"\bsimilar to\b", r"\bresembl", r"\bsort of\b", r"\bkind of (a|an|like)\b", r"\bthink of\b",
    r"\bbasically an?\b", r"\bits own\b", r"\bminiature\b", r"\btiny version\b", r"\bversion of\b",
    r"\bthe way (a|an|your)\b", r"\bpicture (a|an)\b", r"\bit'?s an? [a-z]+ for\b",
]
OUTSIDER_PATTERNS = [
    r"\bhumans?\b", r"\bearthlings?\b", r"\bour species\b", r"\bthis species\b", r"\bcreatures?\b",
    r"\borganisms?\b", r"\bpeople on (this|earth)\b", r"\bon this planet\b", r"\britual",
]
INSIDER_PATTERNS = [r"\bwe\b", r"\bour\b", r"\bus\b", r"\byou know\b", r"\bobviously\b", r"\bjust like\b"]

APPEARANCE_WORDS = {
    "long", "short", "small", "tiny", "big", "large", "round", "flat", "thin", "thick", "plastic", "metal",
    "wooden", "glass", "fabric", "soft", "hard", "shiny", "colour", "color", "shape", "rectangle",
    "circle", "curved", "straight", "black", "white", "red", "blue", "green", "silver", "tall", "heavy",
    "light", "smooth", "rough", "made", "looks", "handle", "tube", "box", "stick",
}
FUNCTION_WORDS = {
    "use", "used", "uses", "using", "helps", "help", "lets", "allows", "makes", "for", "purpose",
    "so", "keeps", "protects", "stops", "carries", "cleans", "need", "needs", "order", "does", "do",
}
MECHANISM_WORDS = {"press", "push", "pull", "twist", "turn", "slide", "click", "open", "close", "fold", "inside", "works"}

# Small common-word list: words outside it count toward vocabulary originality.
COMMON = set(
    """a an the and or but if then so of to in on at by for with from up down out over under into onto
    is are was were be been being am it its it's this that these those there here they them their you your
    i me my we us our he she his her him what which who whom when where why how all any some no not
    do does did done have has had can could will would should may might must just very really much many
    more most less few one two three four five first last thing things stuff something someone people
    person human humans use used uses using make makes made get gets got put puts go goes going come
    like look looks see know need want help lets let keep keeps take takes give gives work works way
    small big little large long short also too again only other another each every own same such
    time day days back front side top bottom end part hand hands head face body water food home house""".split()
)


@dataclass
class TextFeatures:
    words: list[str]
    content_stems: list[str]
    metaphors: list[str] = field(default_factory=list)
    outsider: int = 0
    insider: int = 0
    appearance: int = 0
    function: int = 0
    mechanism: int = 0
    rare_ratio: float = 0.0
    type_token: float = 0.0
    sentences: int = 1

    @property
    def n(self) -> int:
        return len(self.words)


def extract(text: str) -> TextFeatures:
    low = text.lower()
    words = WORD.findall(low)
    content = [stem(w) for w in words if w not in COMMON and len(w) > 2]
    tf = TextFeatures(words=words, content_stems=content)
    for p in METAPHOR_PATTERNS:
        tf.metaphors += [m.group(0) for m in re.finditer(p, low)]
    tf.outsider = sum(len(re.findall(p, low)) for p in OUTSIDER_PATTERNS)
    tf.insider = sum(len(re.findall(p, low)) for p in INSIDER_PATTERNS)
    tf.appearance = sum(1 for w in words if w in APPEARANCE_WORDS)
    tf.function = sum(1 for w in words if w in FUNCTION_WORDS)
    tf.mechanism = sum(1 for w in words if w in MECHANISM_WORDS)
    if words:
        tf.rare_ratio = sum(1 for w in words if w not in COMMON and len(w) >= 6) / len(words)
        tf.type_token = len(set(words)) / len(words)
    tf.sentences = max(1, len([s for s in re.split(r"[.!?]+", text) if s.strip()]))
    return tf


def conventional_ratio(tf: TextFeatures, conventional: list[str]) -> float:
    if not tf.content_stems:
        return 0.0
    conv = {stem(w) for w in conventional}
    return sum(1 for s in tf.content_stems if s in conv) / len(tf.content_stems)


def overlap(a: list[str], b: list[str]) -> float:
    """Share of `a`'s content that already appeared in `b` (redundancy)."""
    if not a:
        return 0.0
    sb = set(b)
    return sum(1 for s in a if s in sb) / len(a)
