"""Thin LLM adapter. Provider-agnostic, no SDK dependency.

Set one of:
  GEMINI_API_KEY                 -> free Gemini (default if present)
  AKS_LLM_PROVIDER=ollama        -> local and free, no key
  AKS_LLM_PROVIDER=anthropic  + ANTHROPIC_API_KEY
  AKS_LLM_PROVIDER=openai     + OPENAI_API_KEY   (or any OpenAI-compatible base URL)
  AKS_LLM_PROVIDER=none          -> offline alien (demo mode)
"""

from __future__ import annotations

import base64
import os
from typing import Optional, Protocol

import httpx


class LLMError(Exception):
    pass


class LLMClient(Protocol):
    name: str

    async def complete(self, system: str, user: str, max_tokens: int = 800) -> str: ...


class AnthropicClient:
    name = "anthropic"

    def __init__(self, api_key: str, model: str, timeout: float = 25.0):
        self.api_key, self.model, self.timeout = api_key, model, timeout

    async def complete(self, system: str, user: str, max_tokens: int = 800) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as http:
            r = await http.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
            )
        if r.status_code != 200:
            raise LLMError(f"anthropic {r.status_code}: {r.text[:300]}")
        data = r.json()
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")

    async def complete_with_images(self, system: str, user: str, image_urls: list[str], max_tokens: int = 600) -> str:
        content = [{"type": "image", "source": {"type": "url", "url": u}} for u in image_urls]
        content.append({"type": "text", "text": user})
        async with httpx.AsyncClient(timeout=45) as http:
            r = await http.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": self.model, "max_tokens": max_tokens, "system": system,
                      "messages": [{"role": "user", "content": content}]},
            )
        if r.status_code != 200:
            raise LLMError(f"anthropic vision {r.status_code}: {r.text[:300]}")
        return "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")


class OpenAIClient:

    def __init__(self, api_key: str, model: str, base_url: str, timeout: float = 25.0, name: str = "openai"):
        self.api_key, self.model, self.base_url, self.timeout = api_key, model, base_url.rstrip("/"), timeout
        self.name = name

    async def complete(self, system: str, user: str, max_tokens: int = 800) -> str:
        r = await self._post({
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        })
        if r.status_code != 200:
            raise LLMError(f"{self.name} {r.status_code}: {r.text[:300]}")
        return r.json()["choices"][0]["message"]["content"] or ""

    async def _post(self, body: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=60) as http:
            r = await http.post(f"{self.base_url}/chat/completions", headers={"authorization": f"Bearer {self.api_key}"}, json=body)
            # Some OpenAI-compatible servers reject response_format; retry once without it
            if r.status_code == 400 and "response_format" in r.text and "response_format" in body:
                body = {k: v for k, v in body.items() if k != "response_format"}
                r = await http.post(f"{self.base_url}/chat/completions", headers={"authorization": f"Bearer {self.api_key}"}, json=body)
        return r

    async def complete_with_images(self, system: str, user: str, image_urls: list[str], max_tokens: int = 600) -> str:
        content: list[dict] = []
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as http:
            for u in image_urls:
                try:
                    img = await http.get(u)
                    if img.status_code == 200 and len(img.content) < 4_000_000:
                        mime = img.headers.get("content-type", "image/jpeg").split(";")[0]
                        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(img.content).decode()}"}})
                except httpx.HTTPError:
                    continue
        if not content:
            raise LLMError("could not download any pin images")
        content.append({"type": "text", "text": user})
        r = await self._post({
            "model": self.model, "max_tokens": max_tokens, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
        })
        if r.status_code != 200:
            raise LLMError(f"{self.name} vision {r.status_code}: {r.text[:300]}")
        return r.json()["choices"][0]["message"]["content"] or ""


def get_client() -> Optional[LLMClient]:
    provider = os.getenv("AKS_LLM_PROVIDER", "").lower().strip()
    model = os.getenv("AKS_LLM_MODEL")
    if provider in ("", "none", "offline"):
        if provider:
            return None
        # No provider named: use whichever key is present
        if os.getenv("GEMINI_API_KEY"):
            provider = "gemini"
        elif os.getenv("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif os.getenv("OPENAI_API_KEY"):
            provider = "openai"
        else:
            return None
    if provider == "gemini":  # free tier, OpenAI-compatible endpoint
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            return None
        return OpenAIClient(key, model or "gemini-3.8-flash",
                            "https://generativelanguage.googleapis.com/v1beta/openai/", name="gemini")
    if provider == "ollama":  # fully local and free, no key
        return OpenAIClient("ollama", model or "qwen2.5vl:3b",
                            os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"), timeout=120, name="ollama")
    if provider == "anthropic":
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            return None
        return AnthropicClient(key, model or "claude-haiku-4-5-20251001")
    if provider == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            return None
        return OpenAIClient(key, model or "gpt-4.1-mini", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    raise ValueError(f"Unknown AKS_LLM_PROVIDER: {provider}")