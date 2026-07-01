"""A2b (contamination triangulation): a logprob membership-inference proxy on DeepSeek.

Textbook Min-K%Prob / teacher-forced NLL scores a GIVEN text's per-token logprobs. The closed
model APIs we use do not expose that: Claude/GPT (9router) return no logprobs, Gemini rejects the
param, and DeepSeek forbids `echo`+`logprobs` together. So teacher-forced MI needs open weights.

What IS computable is a *generation-confidence* proxy: for each task, have the model generate a
solution (temperature 0, logprobs on) from the ORIGINAL prompt and from a meaning-preserving MUTATED
prompt (renamed module + reframed spec — verified function-preserving, scripts/verify_mutants.py).
If the model memorized the canonical (prompt -> solution) pair, it should be systematically MORE
confident (higher mean token logprob) on the original than on the novel-surface mutant. A paired test
with no significant gap ⇒ no memorization advantage; the honesty is reasoning, not recall.

  python3 scripts/membership_probe.py [--n 40]   # DeepSeek (.env), writes results/membership_deepseek.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rtl_gauntlet.llm import _load_dotenv  # noqa: E402

_load_dotenv()
from openai import OpenAI  # noqa: E402

SYS = ("You are an expert Verilog engineer. Given a specification and a module interface, output ONLY "
       "the complete synthesizable Verilog module, no prose, no code fences.")


def prompt_for(task_dir: str) -> tuple[str, str] | None:
    try:
        t = json.load(open(os.path.join(task_dir, "task.json")))
        spec = open(os.path.join(task_dir, t["files"]["spec"])).read()
        return spec + "\n\n" + t.get("interface", ""), t["top"]
    except Exception:  # noqa: BLE001
        return None


def mean_logprob(client: OpenAI, model: str, user: str) -> float | None:
    """Mean per-token logprob of the model's own greedy generation (a confidence proxy)."""
    try:
        r = client.chat.completions.create(
            model=model, temperature=0, max_tokens=400, logprobs=True,
            messages=[{"role": "system", "content": SYS}, {"role": "user", "content": user}])
        lp = r.choices[0].logprobs
        toks = [c.logprob for c in lp.content] if lp and lp.content else []
        return statistics.fmean(toks) if toks else None
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    args = ap.parse_args()
    client = OpenAI(base_url=os.environ["RTLG_BASE_URL"], api_key=os.environ["RTLG_API_KEY"])
    model = os.environ.get("RTLG_MODEL", "deepseek-chat")

    muts = sorted(glob.glob(str(ROOT / "tasks" / "mut_*")))[: args.n]
    rows, diffs = [], []
    for md in muts:
        name = os.path.basename(md).replace("mut_", "")
        od = str(ROOT / "tasks" / f"veval_{name}")
        po, pm = prompt_for(od), prompt_for(md)
        if not (po and pm):
            continue
        lo = mean_logprob(client, model, po[0])
        lm = mean_logprob(client, model, pm[0])
        if lo is None or lm is None:
            continue
        rows.append({"task": name, "logprob_original": round(lo, 4), "logprob_mutated": round(lm, 4),
                     "delta": round(lo - lm, 4)})
        diffs.append(lo - lm)
        print(f"  {name:34s} orig={lo:.3f} mut={lm:.3f} Δ={lo-lm:+.3f}")

    n = len(diffs)
    mean_d = statistics.fmean(diffs) if diffs else 0.0
    # paired sign test: fraction where original is MORE confident (delta>0)
    pos = sum(1 for d in diffs if d > 0)
    out = {"model": model, "n": n, "mean_delta_orig_minus_mut": round(mean_d, 4),
           "frac_original_more_confident": round(pos / n, 3) if n else 0.0,
           "interpretation": ("no memorization advantage (Δ≈0, ~half each way)"
                              if abs(mean_d) < 0.05 and (0.35 <= (pos / max(n, 1)) <= 0.65)
                              else "possible memorization signal — inspect"),
           "rows": rows}
    json.dump(out, open(ROOT / "results" / "membership_deepseek.json", "w"), indent=2)
    print(f"\n{model}: n={n}  mean Δ(orig−mut)={mean_d:+.4f}  "
          f"original-more-confident={pos}/{n} ({100*pos/max(n,1):.0f}%)")
    print(f"  → {out['interpretation']}")
    print("  (Δ≈0 / ~50% ⇒ the model is no more confident on the canonical than on a verified-"
          "equivalent novel mutant ⇒ no contamination advantage.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
