"""C2 analysis: join agentic tokens/iters with the hardened oracle category, then
report the repair-tail payoff and an early-stop trade-off. Offline.

  python scripts/analyze_cost.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rtl_gauntlet.cost import early_stop_tradeoff, iteration_value  # noqa: E402

# Opus hardened categories come from resweep5 (FINAL +reset-BMC stage = 140/156); the
# _p3 files close the residual inconclusive FSMs. Kept consistent with report_cis.py.
PAIRS = [("Opus", ROOT / "results/sweep_opus.json", ROOT / "results/resweep5_opus.json"),
         ("Haiku", ROOT / "results/sweep_haiku.json", ROOT / "results/resweep_haiku_p3.json")]


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
