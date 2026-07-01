"""C1: Cohen's kappa between the LLM tamper-judge and a human, on hardcode-vs-bug.

Reads the human labels filled into docs/c1_annotation.md (each `**Your verdict ...:** `HARDCODE`` or
`BUG`) and the judge/ground-truth key from results/c1_kappa_key.json, then reports Cohen's kappa
(judge vs human) plus each rater's accuracy against ground truth. A high kappa supports the paper's
intent sub-classification; a low one means we soften the intent claim. Stdlib only.

  python3 scripts/c1_kappa.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_human(md_path: Path) -> dict[int, str]:
    """Read each case's filled-in verdict — the value in the backticks AFTER the prompt
    (`...(HARDCODE / BUG):** `HARDCODE``), NOT the `(HARDCODE / BUG)` prompt text itself."""
    text = md_path.read_text()
    out = {}
    for m in re.finditer(
            r"##\s*Case\s*(\d+)\b.*?Your verdict\s*\(HARDCODE\s*/\s*BUG\):\*\*\s*`?\s*([A-Za-z_]+)",
            text, re.DOTALL | re.I):
        v = m.group(2).upper()
        if v in ("HARDCODE", "BUG"):            # ignore the unfilled `____`
            out[int(m.group(1))] = v
    return out


def cohen_kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe != 1 else 1.0


def main() -> int:
    key = json.load(open(ROOT / "results/c1_kappa_key.json"))["key"]
    human = parse_human(ROOT / "docs/c1_annotation.md")
    filled = [k for k in key if k["n"] in human and human[k["n"]] in ("HARDCODE", "BUG")]
    if len(filled) < len(key):
        miss = [k["n"] for k in key if k["n"] not in human or human[k["n"]] not in ("HARDCODE", "BUG")]
        print(f"note: {len(filled)}/{len(key)} cases labelled; unlabelled: {miss}\n"
              "  fill the `____` blanks in docs/c1_annotation.md with HARDCODE or BUG.")
    if not filled:
        return 0
    jv = [k["judge"] for k in filled]
    hv = [human[k["n"]] for k in filled]
    gt = [k["ground_truth"] for k in filled]
    kappa = cohen_kappa(jv, hv)
    j_acc = sum(x == g for x, g in zip(jv, gt)) / len(gt)
    h_acc = sum(x == g for x, g in zip(hv, gt)) / len(gt)
    agree = sum(x == y for x, y in zip(jv, hv))
    print(f"\nC1 inter-rater (n={len(filled)}):")
    print(f"  judge vs human agreement: {agree}/{len(filled)} = {agree/len(filled):.2f}")
    print(f"  Cohen's kappa (judge vs human): {kappa:+.3f}   "
          f"({'strong' if kappa >= 0.8 else 'moderate' if kappa >= 0.6 else 'weak — soften intent claim'})")
    print(f"  accuracy vs ground truth: judge {j_acc:.2f}, human {h_acc:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
