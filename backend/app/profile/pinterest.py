"""Public Pinterest board ingestion.

Uses the public RSS feed Pinterest exposes for boards:
    https://www.pinterest.com/<user>/<board>.rss
No login, no API key. Only works for public boards. RSS returns the most
recent pins (typically up to ~25), which is enough for theme extraction.

The full AKS pipeline (multimodal image analysis) can replace this by posting
a VisualProfile directly to /api/profile.
"""

from __future__ import annotations

import html
import re
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import httpx

from .models import Pin

UA = "Mozilla/5.0 (compatible; AKS/0.1; +https://example.invalid/aks)"


class PinterestError(Exception):
    pass


def parse_board_url(url: str) -> tuple[str, str]:
    """Return (user, board) from a pinterest board URL."""
    u = urlparse(url.strip() if "://" in url else "https://" + url.strip())
    if "pinterest." not in u.netloc:
        raise PinterestError("That does not look like a Pinterest link.")
    parts = [p for p in u.path.split("/") if p]
    if len(parts) < 2 or parts[0] in ("pin", "search", "ideas"):
        raise PinterestError("Paste a board link, like pinterest.com/<user>/<board>/.")
    return parts[0], parts[1]


async def resolve_short_link(url: str) -> str:
    if "pin.it/" not in url:
        return url
    async with httpx.AsyncClient(follow_redirects=True, timeout=10, headers={"user-agent": UA}) as http:
        r = await http.get(url if "://" in url else "https://" + url)
        return str(r.url)


def parse_rss(xml_text: str) -> tuple[str, list[Pin]]:
    root = ET.fromstring(xml_text)
    chan = root.find("channel")
    if chan is None:
        raise PinterestError("Board feed was empty.")
    board_title = (chan.findtext("title") or "").strip()
    pins: list[Pin] = []
    for item in chan.findall("item"):
        desc_html = item.findtext("description") or ""
        img = re.search(r'src="([^"]+)"', desc_html)
        text = html.unescape(re.sub(r"<[^>]+>", " ", desc_html))
        pins.append(
            Pin(
                title=html.unescape((item.findtext("title") or "").strip()),
                description=re.sub(r"\s+", " ", text).strip()[:300],
                image_url=img.group(1) if img else None,
                link=item.findtext("link"),
            )
        )
    return board_title, pins


async def fetch_board(url: str) -> tuple[str, list[Pin], str]:
    url = await resolve_short_link(url)
    user, board = parse_board_url(url)
    feed = f"https://www.pinterest.com/{user}/{board}.rss"
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=12, headers={"user-agent": UA}) as http:
            r = await http.get(feed)
    except httpx.HTTPError as e:
        raise PinterestError(f"Could not reach Pinterest ({e.__class__.__name__}).") from e
    if r.status_code == 404:
        raise PinterestError("Board not found. Is it public?")
    if r.status_code != 200 or "<rss" not in r.text[:500]:
        raise PinterestError(f"Pinterest did not return a feed (status {r.status_code}).")
    title, pins = parse_rss(r.text)
    if not pins:
        raise PinterestError("That board has no public pins.")
    # The URL slug is the board's real name; the feed title is often the user's name
    name = board.replace("-", " ").replace("_", " ").strip() or title
    return name, pins, f"https://www.pinterest.com/{user}/{board}/"
