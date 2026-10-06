"""The visual profile: what AKS learned from someone's saved images.

This is the hand-off point between AKS analysis and AKS games. Any analyzer
(the keyword analyzer here, an LLM, or the full multimodal AKS pipeline) only
has to produce a `VisualProfile`.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Pin(BaseModel):
    title: str = ""
    description: str = ""
    image_url: Optional[str] = None
    link: Optional[str] = None


class Theme(BaseModel):
    name: str  # canonical theme key, e.g. "architecture"
    label: str  # display, e.g. "ARCHITECTURE"
    weight: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)  # pin titles that triggered it


class VisualProfile(BaseModel):
    source: Literal["demo", "pinterest", "manual"] = "manual"
    board_name: str = ""
    board_url: Optional[str] = None
    pin_count: int = 0
    themes: list[Theme] = Field(default_factory=list)
    sample_pins: list[Pin] = Field(default_factory=list)
    reflection: list[str] = Field(default_factory=list)  # short AKS "reflection" lines
    # How the board was read: "keywords" (text only), "text-llm", or "vision" (images seen)
    analysis: Literal["keywords", "text-llm", "vision", "demo"] = "keywords"
    aesthetic: list[str] = Field(default_factory=list)  # visual qualities: palette, mood, composition
    motifs: list[str] = Field(default_factory=list)  # recurring things across pins
    contradiction: Optional[str] = None  # a tension in what they save
    analysis_note: Optional[str] = None  # why richer analysis did not run, if it didn't

    def top_themes(self, k: int = 4) -> list[Theme]:
        return sorted(self.themes, key=lambda t: -t.weight)[:k]
