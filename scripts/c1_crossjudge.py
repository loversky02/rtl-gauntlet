"""Tier-4a: de-Opus the judge study — a SECOND independent judge on the same 20 blind cases.

Round-4 reviewer: the reliable-judge result carries Opus's fingerprint (Opus was the only judge).
Here we rebuild the exact same 20-case set (same seed-7 shuffle, comment-stripped) and judge it with a
DIFFERENT model (e.g. Gemini via .env.gemini), then report: accuracy vs ground truth, agreement +
Cohen's kappa vs the stored Opus verdicts, and kappa vs the human annotations. Does NOT touch
docs/c1_annotation.md or the answer key.

  env $(grep -v '^#' .env.gemini | xargs) python3 scripts/c1_crossjudge.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from c1_build_annotation import CONSTRUCTED, REAL, strip_comments  # noqa: E402
from c1_kappa import cohen_kappa, parse_human  # noqa: E402
from rtl_gauntlet.schema import FORMAL_CEX  # noqa: E402
from rtl_gauntlet.tamper_judge import HARDCODE_OVERFIT, classify_exploit  # noqa: E402


def main() -> int:
    from rtl_gauntlet.llm import LLMClient
    judge = LLMClient()
    cases = []
    for cid, sp, dp in REAL:
        s, d = ROOT / sp, ROOT / dp
        if s.exists() and d.exists():
            cases.append((cid, s.read_text(), strip_comments(d.read_text()), "HARDCODE"))
    for cid, spec, design, gt in CONSTRUCTED:
        cases.append((cid, spec, strip_comments(design), gt))
    random.Random(7).shuffle(cases)                      # SAME order as the original study

    key = {k["n"]: k for k in json.load(open(ROOT / "results/c1_kappa_key.json"))["key"]}
    human = parse_human(ROOT / "docs/c1_annotation.md")

    rows, new_v, opus_v, human_v, gt_v = [], [], [], [], []
    print(f"cross-judge = {judge.model}; {len(cases)} cases")
    for i, (cid, spec, design, gt) in enumerate(cases, 1):
        v = classify_exploit(design, spec, FORMAL_CEX, edited_non_design=False,
                             tb_changed=False, llm=judge)
        jv = "HARDCODE" if v.subtype == HARDCODE_OVERFIT else "BUG"
        rows.append({"n": i, "case": cid, "judge2": jv, "judge1_opus": key[i]["judge"],
                     "human": human.get(i, ""), "ground_truth": gt})
        new_v.append(jv); opus_v.append(key[i]["judge"]); gt_v.append(gt)
        human_v.append(human.get(i, ""))
        print(f"  [{i:2d}] {cid:20s} {judge.model.split('/')[-1]}={jv:9s} opus={key[i]['judge']:9s} gt={gt}")

    acc = sum(a == b for a, b in zip(new_v, gt_v)) / len(gt_v)
    k_oj = cohen_kappa(new_v, opus_v)
    k_h = cohen_kappa(new_v, [h for h in human_v]) if all(human_v) else float("nan")
    out = {"judge2_model": judge.model, "n": len(rows),
           "judge2_acc_vs_gt": round(acc, 3),
           "kappa_judge2_vs_opusjudge": round(k_oj, 3),
           "kappa_judge2_vs_human": round(k_h, 3), "rows": rows}
    json.dump(out, open(ROOT / "results/c1_crossjudge.json", "w"), indent=1)
    print(f"\n{judge.model}: acc vs GT = {acc:.2f} | κ vs Opus-judge = {k_oj:+.3f} | "
          f"κ vs human = {k_h:+.3f}")
    print("  -> two independent judges agreeing = the reliability is a property of the method, not of Opus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
