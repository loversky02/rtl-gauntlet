"""Confirm the configured model gateway is reachable (RTLG_* / .env auto-loaded).

Run after filling in .env:
    python3 scripts/check_llm.py
Prints the resolved base_url/model, whether a key is set, and a one-token live ping.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    from rtl_gauntlet.llm import LLMClient  # importing triggers the .env load

    base = os.getenv("RTLG_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "(OpenAI default)"
    key = os.getenv("RTLG_API_KEY") or os.getenv("OPENAI_API_KEY")
    model = os.getenv("RTLG_MODEL", "gpt-5.5")
    print(f"base_url = {base}")
    print(f"model    = {model}")
    print(f"api_key  = {'set (' + str(len(key)) + ' chars)' if key else 'MISSING'}")
    if not key:
        print("\n  ✗ RTLG_API_KEY is empty — edit .env, paste your DeepSeek key, rerun.")
        return 1
    try:
        c = LLMClient()
        r = c.complete("You are a terse assistant.", "Reply with exactly the two characters: OK")
        print(f"\n  ✓ gateway reachable — reply={r.content!r}  "
              f"(prompt={r.prompt_tokens}, completion={r.completion_tokens}, cached={r.cached_tokens})")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"\n  ✗ call failed: {type(e).__name__}: {e}")
        print("    check RTLG_BASE_URL / RTLG_MODEL / key validity (and `pip install openai`).")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
