"""C3 rank-stability: Kendall-τ of the design PPA ranking across synthesis strategies.

The reviewer asks whether the PPA ordering of designs is an artifact of one synthesis flow. We rank
the size-graded designs by each metric under ≥2 OpenLane SYNTH_STRATEGY settings and report Kendall-τ
between the rankings. τ≈1 ⇒ the ranking is stable (the latency-axis comparison is meaningful); a low τ
⇒ rankings flip across flows (a real threat we would then flag). Stdlib only.

  python3 scripts/kendall_tau.py [results/ppa_graded.jsonl]
"""
from __future__ import annotations

import itertools
import json
import sys
from collections import defaultdict


def kendall_tau(order_a: list[str], order_b: list[str]) -> float:
    """τ-b over the shared items, from two rank-orderings (lists of design ids best→worst)."""
    common = [x for x in order_a if x in order_b]
    ra = {d: i for i, d in enumerate(order_a)}
    rb = {d: i for i, d in enumerate(order_b)}
    n = len(common)
    if n < 2:
        return float("nan")
    conc = disc = 0
    for i, j in itertools.combinations(common, 2):
        s = (ra[i] - ra[j]) * (rb[i] - rb[j])
        conc += s > 0
        disc += s < 0
    return (conc - disc) / (n * (n - 1) / 2)


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "results/ppa_graded.jsonl"
    rows = [json.loads(l) for l in open(path) if l.strip()]
    # group metrics by strategy: {strategy: {design: {area,power,slack}}}
    by_strat: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in rows:
        strat = r.get("strategy", "default")
        by_strat[strat][r["task"]] = {"area": r.get("area_um2", 0),
                                      "power": r.get("power_mw", 0),
                                      "slack": -r.get("timing_ns", 0)}
    strats = sorted(by_strat)
    print(f"strategies: {strats}   designs: {sorted({d for s in by_strat.values() for d in s})}")
    if len(strats) < 2:
        print("need >=2 strategies for a rank-stability τ — rerun gen_ppa_data with --strategies "
              "'AREA 0,DELAY 0'.")
        return 0
    a, b = strats[0], strats[1]
    print(f"\nKendall-τ of the design ranking, '{a}' vs '{b}':")
    for metric in ("area", "power", "slack"):
        common = sorted(set(by_strat[a]) & set(by_strat[b]))
        oa = sorted(common, key=lambda d: by_strat[a][d][metric])
        ob = sorted(common, key=lambda d: by_strat[b][d][metric])
        tau = kendall_tau(oa, ob)
        verdict = "STABLE" if tau >= 0.8 else ("moderate" if tau >= 0.5 else "UNSTABLE (flips)")
        print(f"  {metric:6s}: τ = {tau:+.3f}   ({verdict})   n={len(common)}")
    print("\n  τ≈1 ⇒ the size-graded ranking holds across synthesis strategies (pre-signoff, relative).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
