"""C2 analysis: join agentic tokens/iters with the hardened oracle category, then
report the repair-tail payoff and an early-stop trade-off. Offline.

  python scripts/analyze_cost.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rtl_gauntlet.cost import early_stop_tradeoff, iteration_value  # noqa: E402

PAIRS = [("Opus", "results/sweep_opus.json", "results/resweep3_opus.json"),
         ("Haiku", "results/sweep_haiku.json", "results/resweep_haiku_sv.json")]


def load(agent_f, hard_f):
    agent = {r["task"]: r for r in json.load(open(agent_f))["rows"] if r.get("tokens")}
    hard = {r["task"]: r for r in json.load(open(hard_f))["rows"]}
    rows = []
    for t, a in agent.items():
        rows.append({"task": t, "iters": a.get("iters", 1), "tokens": a.get("tokens", 0),
                     "category": hard.get(t, {}).get("category", a.get("category"))})
    return rows


def main() -> int:
    for name, af, hf in PAIRS:
        try:
            rows = load(af, hf)
        except FileNotFoundError:
            continue
        print(f"\n=== {name} ({len(rows)} tasks) ===")
        print("  repair-tail payoff:", iteration_value(rows))
        print("  early-stop @1 iter:", early_stop_tradeoff(rows, 1))
    print("\n  Interpretation: payoff_rate = fraction of multi-iter tasks whose extra "
          "iteration ended honest; a low rate means the tail is mostly wasted budget that "
          "an early-stop policy reclaims at little honesty cost.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
