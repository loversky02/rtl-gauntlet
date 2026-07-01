"""A2b (proper): teacher-forced membership inference on an OPEN model, via local MLX.

The closed-model APIs we evaluate expose no teacher-forced logprobs, so textbook Min-K%Prob / NLL
membership inference is impossible there (see membership_probe.py). Here we run it PROPERLY on an open
model (Qwen2.5-3B-Instruct-4bit) whose per-token logprobs we compute locally with MLX. For each task we
teacher-force the canonical solution given the ORIGINAL prompt and given the meaning-preserving MUTATED
prompt (renamed module + reframed spec — verified function-preserving). If the model memorized the
canonical (prompt -> solution) pair, the mutant should be MORE surprising: NLL(mutant) > NLL(original)
and lower Min-K%. A paired difference ~0 ⇒ no memorization advantage — the honesty is reasoning.

  python3 scripts/membership_mlx.py [--n 40] [--model mlx-community/Qwen2.5-3B-Instruct-4bit]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import sys
from pathlib import Path

import mlx.core as mx
from mlx_lm import load

ROOT = Path(__file__).resolve().parents[1]


def solution(task_dir: str) -> tuple[str, str] | None:
    """(prompt, golden-solution) for a task dir."""
    try:
        t = json.load(open(os.path.join(task_dir, "task.json")))
        spec = open(os.path.join(task_dir, t["files"]["spec"])).read()
        golden = open(os.path.join(task_dir, t["files"]["golden"])).read()
        return f"{spec}\n\n{t.get('interface','')}\n", golden
    except Exception:  # noqa: BLE001
        return None


def score(model, tok, prompt: str, completion: str) -> tuple[float, float]:
    """(NLL, Min-20%-mean-logprob) of `completion` teacher-forced after `prompt`."""
    pids = tok.encode(prompt)
    full = tok.encode(prompt + completion)
    cids = full[len(pids):]
    if not cids:
        return float("nan"), float("nan")
    ids = mx.array(full)[None]
    logits = model(ids[:, :-1])
    logp = logits - mx.logsumexp(logits, axis=-1, keepdims=True)   # log-softmax
    tgt = ids[0, 1:]
    lp = logp[0, mx.arange(tgt.shape[0]), tgt]
    comp = [float(x) for x in lp[len(pids) - 1:]]                  # completion-token logprobs
    k = max(1, len(comp) // 5)
    return -statistics.fmean(comp), statistics.fmean(sorted(comp)[:k])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--model", default="mlx-community/Qwen2.5-3B-Instruct-4bit")
    args = ap.parse_args()
    print(f"loading {args.model} ...", flush=True)
    model, tok = load(args.model)

    rows, dnll, dmink = [], [], []
    for md in sorted(glob.glob(str(ROOT / "tasks" / "mut_*")))[: args.n]:
        name = os.path.basename(md).replace("mut_", "")
        orig = solution(str(ROOT / "tasks" / f"veval_{name}"))
        mut = solution(md)
        if not (orig and mut):
            continue
        nll_o, mk_o = score(model, tok, *orig)
        nll_m, mk_m = score(model, tok, *mut)
        rows.append({"task": name, "nll_orig": round(nll_o, 3), "nll_mut": round(nll_m, 3),
                     "mink_orig": round(mk_o, 3), "mink_mut": round(mk_m, 3),
                     "dnll_mut_minus_orig": round(nll_m - nll_o, 3)})
        dnll.append(nll_m - nll_o)
        dmink.append(mk_o - mk_m)
        print(f"  {name:32s} NLL orig={nll_o:.2f} mut={nll_m:.2f} Δ={nll_m-nll_o:+.2f}", flush=True)

    n = len(dnll)
    mean_dnll = statistics.fmean(dnll) if dnll else 0.0
    pos = sum(1 for d in dnll if d > 0.02)
    out = {"model": args.model, "n": n, "mean_dNLL_mut_minus_orig": round(mean_dnll, 4),
           "frac_mut_more_surprising": round(pos / n, 3) if n else 0.0,
           "interpretation": ("no memorization advantage (ΔNLL≈0: the mutant is no more surprising "
                              "than the canonical)" if abs(mean_dnll) < 0.1 else
                              "possible memorization (mutant systematically more surprising) — inspect"),
           "rows": rows}
    json.dump(out, open(ROOT / "results" / "membership_mlx.json", "w"), indent=2)
    print(f"\n{args.model}: n={n}  mean ΔNLL(mut−orig)={mean_dnll:+.4f}  "
          f"mut-more-surprising={pos}/{n}")
    print(f"  → {out['interpretation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
