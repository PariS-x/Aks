"""Forbidden-term detection.

Deterministic, explainable, and deliberately narrow. The goal is to catch the
object's name and the handful of words that give it away, not to turn the game
into a thesaurus exam. So:

* matching is on whole words after light stemming ("brushing" -> "brush"),
  never on substrings ("oral" does not match "moral");
* multi-word names are matched as phrases, and also when the player joins or
  hyphenates them ("seat-belt", "seatbelt");
* compound words only count when they *start or end* with the object's name
  ("toothbrushes", "forklift" is allow-listed per object);
* obvious evasions are caught and flagged as such ("t00th", "t o o t h").
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import TargetObject, Violation

_TOKEN = re.compile(r"[A-Za-z0-9@$']+")
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})
_IRREGULAR = {"teeth": "tooth", "feet": "foot", "geese": "goose", "mice": "mouse", "men": "man", "women": "woman"}


def stem(word: str) -> str:
    w = word.lower().strip("'")
    if w.endswith("'s"):
        w = w[:-2]
    if w in _IRREGULAR:
        return _IRREGULAR[w]
    for suf, rep in (("ies", "y"), ("sses", "ss"), ("ches", "ch"), ("shes", "sh"), ("xes", "x"), ("zes", "z")):
        if w.endswith(suf) and len(w) > len(suf) + 2:
            return w[: -len(suf)] + rep
    if w.endswith("ing") and len(w) > 5:
        w = w[:-3]
        if len(w) > 2 and w[-1] == w[-2] and w[-1] not in "ls":
            w = w[:-1]
        return w
    if w.endswith("ed") and len(w) > 4:
        w = w[:-2]
        if len(w) > 2 and w[-1] == w[-2] and w[-1] not in "ls":
            w = w[:-1]
        return w
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    return w


@dataclass
class _Tok:
    raw: str
    start: int
    end: int
    norm: str  # leet-normalised, lowercase
    stem: str
    evasive: bool


def _tokenize(text: str) -> list[_Tok]:
    toks: list[_Tok] = []
    for m in _TOKEN.finditer(text):
        raw = m.group(0)
        low = raw.lower()
        norm = low.translate(_LEET)
        evasive = norm != low and any(c.isalpha() for c in low)
        # Numbers alone are not words ("4 legs" stays "4")
        if not any(c.isalpha() for c in low):
            norm, evasive = low, False
        toks.append(_Tok(raw, m.start(), m.end(), norm, stem(norm), evasive))
    return _merge_spelled_out(toks, text)


def _merge_spelled_out(toks: list[_Tok], text: str) -> list[_Tok]:
    """Join runs of single letters ("t o o t h") into one evasive token."""
    out: list[_Tok] = []
    i = 0
    while i < len(toks):
        j = i
        while j < len(toks) and len(toks[j].norm) == 1 and toks[j].norm.isalpha():
            j += 1
        if j - i >= 3:
            joined = "".join(t.norm for t in toks[i:j])
            out.append(_Tok(text[toks[i].start : toks[j - 1].end], toks[i].start, toks[j - 1].end, joined, stem(joined), True))
            i = j
        else:
            out.append(toks[i])
            i += 1
    return out


class ConstraintChecker:
    def __init__(self, target: TargetObject):
        self.target = target
        self.allowed = {stem(w) for w in target.allowed_lookalikes}
        # (term_stems, joined_stem, tier, canonical)
        self.terms: list[tuple[list[str], str, str, str]] = []
        for ft in target.forbidden_terms:
            parts = [stem(p) for p in _TOKEN.findall(ft.term.lower())]
            joined = stem("".join(p.lower() for p in _TOKEN.findall(ft.term)))
            self.terms.append((parts, joined, ft.tier, ft.term))
        # Longest phrases first so "seat belt" wins over "belt"
        self.terms.sort(key=lambda t: -len(t[0]))
        self.name_stems = {t[1] for t in self.terms if t[2] == "name" and len(t[1]) >= 4}

    def check(self, text: str) -> list[Violation]:
        toks = _tokenize(text)
        used = [False] * len(toks)
        out: list[Violation] = []

        for parts, joined, tier, canon in self.terms:
            n = len(parts)
            if n >= 2:  # "trafficlight" typed as one word
                for i, t in enumerate(toks):
                    if not used[i] and t.stem == joined:
                        self._add(out, used, i, 1, [t], text, tier, canon)
            for i in range(len(toks) - n + 1):
                if any(used[i : i + n]):
                    continue
                window = toks[i : i + n]
                hit = [t.stem for t in window] == parts
                # "seatbelt" typed as one word / "tooth-brush" as two
                if not hit and n == 1 and i + 1 < len(toks):
                    pair = toks[i : i + 2]
                    if not any(used[i : i + 2]) and stem(pair[0].norm + pair[1].norm) == joined and text[pair[0].end : pair[1].start] in ("-", " ", ""):
                        window, hit, n_used = pair, True, 2
                        self._add(out, used, i, n_used, window, text, tier, canon)
                        continue
                if hit:
                    self._add(out, used, i, n, window, text, tier, canon)

        # Compounds that start or end with the object's name: "toothbrushes"
        for i, t in enumerate(toks):
            if used[i] or t.stem in self.allowed or len(t.norm) < 5:
                continue
            for ns in self.name_stems:
                if t.norm != ns and (t.norm.startswith(ns) or t.norm.endswith(ns)):
                    self._add(out, used, i, 1, [t], text, "name", ns)
                    break

        out.sort(key=lambda v: v.start)
        return out

    def _add(self, out, used, i, n, window, text, tier, canon):
        if n == 1 and window[0].stem in self.allowed:
            return
        for k in range(i, i + n):
            used[k] = True
        start, end = window[0].start, window[-1].end
        out.append(
            Violation(
                term=canon, matched=text[start:end], start=start, end=end,
                tier=tier, evasion=any(t.evasive for t in window),
            )
        )


def visible_forbidden(target: TargetObject) -> list[str]:
    """The forbidden list shown to the player.

    Name-tier terms (the name and its aliases) are enforced but never listed:
    listing "stoplight" would hand the player the answer the screen is hiding.
    """
    shown = ["ITS HUMAN NAME"]
    for ft in target.forbidden_terms:
        if ft.tier == "revealing" and ft.visible:
            shown.append(ft.term.upper())
    return shown


def redact_name(text: str, target: TargetObject) -> str:
    """Stop the alien from blurting the answer before the round is won."""
    out = text
    for term in sorted({target.name, *target.aliases}, key=len, reverse=True):
        out = re.sub(rf"\b{re.escape(term)}(e?s)?\b", "[REDACTED HUMAN WORD]", out, flags=re.I)
    return out
