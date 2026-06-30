"""Minimal OpenAI-compatible client, pointed at the 9router gateway.

Mirrors CVDP's openrouter_factory pattern (openai SDK + custom base_url), so the
only thing that changes vs. a normal OpenAI call is the gateway URL. Routed models
(GPT-5.5 / Claude / Gemini) are ~free on 9router; that is why the Honesty + Cost
sweeps don't need local GPU.

Config via env (record these for reproducibility — R20):
  RTLG_BASE_URL   gateway endpoint (e.g. http://localhost:9router/v1)
  RTLG_API_KEY    gateway key
  RTLG_MODEL      exact model id, pinned (e.g. gpt-5.5 / claude-opus-4-6)
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMClient:
    def __init__(self, model: str | None = None, base_url: str | None = None,
                 api_key: str | None = None):
        from openai import OpenAI  # lazy: core library stays import-free without deps

        self.model = model or os.getenv("RTLG_MODEL", "gpt-5.5")
        base_url = base_url or os.getenv("RTLG_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        api_key = (api_key or os.getenv("RTLG_API_KEY")
                   or os.getenv("OPENAI_API_KEY") or "sk-noauth")
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def complete(self, system: str, user: str, timeout: int = 180) -> LLMResponse:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout=timeout,
        )
        usage = resp.usage
        cached = 0
        details = getattr(usage, "prompt_tokens_details", None)
        if details is not None:
            cached = getattr(details, "cached_tokens", 0) or 0
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            cached_tokens=cached,
        )
