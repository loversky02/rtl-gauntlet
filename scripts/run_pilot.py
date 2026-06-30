"""Run the two-tier pilot. Requires iverilog + yosys (→ RunPod / sim image).

Modes:
  --baselines           score the honest (golden) + dishonest (planted) anchors,
                        NO LLM. Proves the oracle catches over-fitting (R19).
  --candidate FILE      score one RTL file under the task dir, NO LLM.
  (default)             run the agentic loop via 9router, then withheld scoring.

Examples:
  python scripts/run_pilot.py --task tasks/pilot_gray2bin --baselines
  RTLG_BASE_URL=... RTLG_MODEL=gpt-5.5 python scripts/run_pilot.py --task tasks/pilot_gray2bin
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rtl_gauntlet.metrics import summary  # noqa: E402
from rtl_gauntlet.runner import evaluate_candidate, evaluate_task, load_task  # noqa: E402
from rtl_gauntlet.schema import AgentRun, Tier  # noqa: E402


def print_run(run: AgentRun) -> None:
    print(f"\n  ● {run.task_id}  (model={run.model}, iters={run.iterations}, "
          f"tok={run.total_tokens:,})")
    for t in (Tier.VISIBLE, Tier.HIDDEN, Tier.FORMAL):
        o = run.outcome(t)
        if o is None:
            continue
        mark = "✓" if o.passed else "✗"
        extra = f" [{o.status or o.detail}]" if (o.status or o.detail) else ""
        print(f"      {mark} {t.value:8s}{extra}")
    print(f"      → honest_pass = {run.is_honest_pass}")


def print_summary(runs: list[AgentRun]) -> None:
    s = summary(runs)
    print("\n  ── metrics ──")
    print(f"     visible_pass_rate  : {s['visible_pass_rate']:.2f}")
    print(f"     honest_pass_rate   : {s['honest_pass_rate']:.2f}   (HPR)")
    print(f"     reward_hacking_gap : {s['reward_hacking_gap']:.2f}   (RHG)")
    print(f"     tier_gap           : {s['tier_gap']:.2f}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="tasks/pilot_gray2bin")
    ap.add_argument("--workdir", default="runs/pilot")
    ap.add_argument("--candidate", help="RTL filename under the task dir (no LLM)")
    ap.add_argument("--baselines", action="store_true",
                    help="score honest + dishonest anchors (no LLM)")
    ap.add_argument("--max-iters", type=int, default=5)
    args = ap.parse_args()

    task = load_task(args.task)
    runs: list[AgentRun] = []

    if args.baselines:
        for label, fname in task.get("baselines", {}).items():
            rtl = os.path.join(args.task, fname)
            wd = os.path.join(args.workdir, label)
            runs.append(evaluate_candidate(args.task, rtl, wd, label=label))
    elif args.candidate:
        rtl = os.path.join(args.task, args.candidate)
        runs.append(evaluate_candidate(args.task, rtl, args.workdir,
                                       label=Path(args.candidate).stem))
    else:
        from rtl_gauntlet.llm import LLMClient
        run, traj = evaluate_task(args.task, args.workdir, LLMClient(),
                                  max_iters=args.max_iters)
        runs.append(run)
        print(f"\n  trajectory: {[ (h.iteration, h.visible_passed) for h in traj.history ]}")

    for r in runs:
        print_run(r)
    print_summary(runs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
