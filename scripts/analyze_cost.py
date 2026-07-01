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

from rtl_gauntlet.cost import (  # noqa: E402
    early_stop_tradeoff,
    iteration_value,
    prospective_early_stop,
)

# Agent tokens/iters from the per-model sweeps; hardened category from the careset re-scores
# (careset_equiv counts honest — consistent with report_cis.py). DeepSeek is omitted: its agent
# sweep did not record per-task token/iteration data.
PAIRS = [("Opus", ROOT / "results/sweep_opus.json", ROOT / "results/resweep_opus_careset.json"),
         ("Haiku", ROOT / "results/sweep_haiku.json", ROOT / "results/resweep_haiku_careset.json"),
         ("GPT-5.5", ROOT / "results/sweep_gpt55.json", ROOT / "results/resweep_gpt_careset.json"),
         ("Gemini", ROOT / "results/sweep_gemini.json", ROOT / "results/resweep_gemini_careset.json")]


def load(agent_f, hard_f):
    agent = {r["task"]: r for r in json.load(open(agent_f))["rows"] if r.get("tokens")}
    hard = {r["task"]: r for r in json.load(open(hard_f))["rows"]}
    rows = []
    for t, a in agent.items():
        rows.append({"task": t, "iters": a.get("iters", 1), "tokens": a.get("tokens", 0),
                     "category": hard.get(t, {}).get("category", a.get("category"))})
    return rows


def main() -> int:
    per_model = {}
    for name, af, hf in PAIRS:
        try:
            rows = load(af, hf)
        except FileNotFoundError:
            continue
        per_model[name] = rows
        iv = iteration_value(rows)
        print(f"\n=== {name} ({len(rows)} tasks) ===")
        print(f"  repair-tail payoff: {iv}")
        print("  early-stop ablation (post-hoc):")
        for k in (1, 2, 3):
            t = early_stop_tradeoff(rows, k)
            loss = round(100 * t["honest_lost"] / t["honest_total"], 1) if t["honest_total"] else 0.0
            print(f"    @{k}: tokens_saved={t['tokens_saved_pct']:5.1f}%  "
                  f"honest_lost={t['honest_lost']:2d} ({loss:.1f}%)  capped={t['tasks_capped']}")

    # PROSPECTIVE: fit the cap on the other models, apply to the held-out one (out-of-sample).
    print("\n=== prospective early-stop (leave-one-model-out; k fit on the others, "
          "honesty-loss budget 5%) ===")
    names = list(per_model)
    for held in names:
        train = [r for m in names if m != held for r in per_model[m]]
        p = prospective_early_stop(train, per_model[held], ks=(1, 2, 3), max_honest_loss_pct=5.0)
        print(f"  {held:8s} -> chose k={p['chosen_k']} on the other {len(names)-1} models: "
              f"realized tokens_saved={p['test_tokens_saved_pct']:.1f}%, "
              f"honest_lost={p['test_honest_lost']} ({p['test_honest_lost_pct']:.1f}%)")

    print("\n  Interpretation: payoff_rate = fraction of multi-iter tasks whose extra iteration "
          "ended honest (low ⇒ wasted tail). The prospective pass tunes k WITHOUT seeing the "
          "held-out model, so its savings/loss are out-of-sample, not post-hoc.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
