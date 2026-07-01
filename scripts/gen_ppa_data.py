"""Build a (RTL features → PPA) dataset for the C3 surrogate.

Default = mock PPA (offline, no tools). `--openlane` runs the real Sky130 flow on a
RunPod box. The design corpus is every golden.v + every agent candidate we have.

  python scripts/gen_ppa_data.py                 # mock, offline
  python scripts/gen_ppa_data.py --openlane       # real (RunPod, slow)
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rtl_gauntlet.ppa import extract_features, mock_ppa, ppa_to_row, run_openlane  # noqa: E402


def corpus(task_glob: str = "tasks/*") -> list[tuple[str, str, str]]:
    """(label, rtl_path, top) over goldens matching `task_glob`; candidates only for the full corpus."""
    items = []
    for g in sorted(glob.glob(os.path.join(task_glob, "golden.v"))):
        task = os.path.basename(os.path.dirname(g))
        top = json.load(open(os.path.join(os.path.dirname(g), "task.json")))["top"]
        items.append((f"{task}:golden", g, top))
    if task_glob == "tasks/*":
        for c in sorted(glob.glob("runs/sweep_opus/*/candidate.v"))[:400]:
            task = os.path.basename(os.path.dirname(c))
            items.append((f"{task}:opus", c, "TopModule"))
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--openlane", action="store_true")
    ap.add_argument("--out", default="results/ppa_dataset.jsonl")
    ap.add_argument("--workdir", default="runs/ppa")
    ap.add_argument("--limit", type=int, default=0, help="cap # designs (0=all); real P&R is slow")
    ap.add_argument("--glob", default="tasks/*", help="task-dir glob (e.g. 'tasks/ppa_*' for the graded set)")
    ap.add_argument("--strategies", default="",
                    help="comma-sep OpenLane SYNTH_STRATEGY values for a rank-stability sweep "
                         "(e.g. 'AREA 0,DELAY 0'); empty = the default strategy once")
    args = ap.parse_args()

    items = corpus(args.glob)
    if args.limit:
        items = items[: args.limit]
    strategies = [s.strip() for s in args.strategies.split(",") if s.strip()] or [None]
    print(f"# {len(items)} designs x {len(strategies)} strateg(ies), "
          f"source={'openlane' if args.openlane else 'mock'}", flush=True)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    n_ok = 0
    with open(args.out, "w") as out:
        for i, (label, rtl, top) in enumerate(items, 1):
            feats = extract_features(rtl)
            for strat in strategies:
                tag = label + (f"@{strat.replace(' ', '')}" if strat else "")
                try:
                    if args.openlane:
                        extra = {"SYNTH_STRATEGY": strat} if strat else None
                        ppa = run_openlane(rtl, top, os.path.join(args.workdir, tag.replace(":", "_")),
                                           config_extra=extra)
                    else:
                        ppa = mock_ppa(feats)
                    if ppa.ok:
                        row = ppa_to_row(label, rtl, ppa)
                        if strat:
                            row["strategy"] = strat
                        out.write(json.dumps(row) + "\n")
                        out.flush()
                        n_ok += 1
                        print(f"  ok {tag}: area={ppa.area_um2:.0f} power={ppa.power_mw:.3f} "
                              f"slack={-ppa.timing_ns:.2f}", flush=True)
                    else:
                        print(f"  fail {tag} (no metrics)", flush=True)
                except Exception as e:  # noqa: BLE001
                    print(f"  skip {tag}: {e}", flush=True)
    print(f"wrote {n_ok} rows → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
