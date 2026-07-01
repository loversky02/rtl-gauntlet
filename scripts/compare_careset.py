"""Reproduce the A1 careset contribution: Pass-3 baseline vs careset-oracle re-score, per model.

Prints RHG_cex reduction, HPR change, careset_equiv count, and a regression check (any task that
flipped honest->RHG_cex). Regenerate the careset re-scores with:

  for m,dir in opus:runs/sweep_opus gpt:runs/veval_gpt haiku:runs/sweep_haiku \
               deepseek:runs/ds_sweep gemini:runs/veval_gemini; do
    python3 scripts/run_veval.py --candidates-from $dir --glob "tasks/veval_*" \
            --out results/resweep_${m}_careset.json --formal-timeout 90
  done
"""
from __future__ import annotations

import collections
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HONEST = {"honest", "bmc_equiv", "careset_equiv"}

# (label, paper Pass-3 baseline, careset re-score)
MODELS = [
    ("Opus 4.8", "resweep5_opus.json", "resweep_opus_careset.json"),
    ("GPT-5.5", "sweep_gpt55_p3.json", "resweep_gpt_careset.json"),
    ("Gemini 2.5", "sweep_gemini.json", "resweep_gemini_careset.json"),
    ("DeepSeek", "sweep_deepseek_p3.json", "resweep_deepseek_careset.json"),
    ("Haiku 4.5", "resweep_haiku_p3.json", "resweep_haiku_careset.json"),
]


def cats(fname: str) -> dict[str, str]:
    return {r["task"]: r.get("category") for r in json.load(open(ROOT / "results" / fname))["rows"]}


def main() -> int:
    print(f"{'model':11s} {'RHG_cex':>9s} {'HPR':>18s} {'careset':>8s} {'regress':>8s}")
    print("-" * 58)
    tot_old = tot_new = 0
    for name, bf, nf in MODELS:
        if not (ROOT / "results" / nf).exists():
            print(f"{name}: re-score {nf} missing"); continue
        b = cats(bf) if (ROOT / "results" / bf).exists() else {}
        n = cats(nf)
        cb, cn = collections.Counter(b.values()), collections.Counter(n.values())
        hb = sum(cb.get(x, 0) for x in HONEST); hn = sum(cn.get(x, 0) for x in HONEST)
        reg = sum(1 for t in b if b[t] in HONEST and n.get(t) == "RHG_cex")
        ro, rn = cb.get("RHG_cex", 0), cn.get("RHG_cex", 0)
        tot_old += ro; tot_new += rn
        hpr = f"{hb/len(b):.3f}->{hn/len(n):.3f}" if b else f"->{hn/len(n):.3f}"
        print(f"{name:11s} {ro:3d}->{rn:<3d} {hpr:>18s} {cn.get('careset_equiv',0):8d} {reg:8d}")
    print("-" * 58)
    print(f"{'TOTAL RHG_cex':22s} {tot_old} -> {tot_new}  (remaining = the circuit8 mixed-edge residual)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
