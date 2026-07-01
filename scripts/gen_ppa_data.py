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


def corpus() -> list[tuple[str, str, str]]:
    """(label, rtl_path, top) over goldens + candidates."""
    items = []
    for g in sorted(glob.glob("tasks/*/golden.v")):
        task = os.path.basename(os.path.dirname(g))
        top = json.load(open(os.path.join(os.path.dirname(g), "task.json")))["top"]
        items.append((f"{task}:golden", g, top))
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
    args = ap.parse_args()

    items = corpus()
    if args.limit:
        items = items[: args.limit]
    print(f"# {len(items)} designs, source={'openlane' if args.openlane else 'mock'}", flush=True)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    n_ok = 0
    with open(args.out, "w") as out:
        for i, (label, rtl, top) in enumerate(items, 1):
            try:
                feats = extract_features(rtl)
                ppa = (run_openlane(rtl, top, os.path.join(args.workdir, label.replace(":", "_")))
                       if args.openlane else mock_ppa(feats))
                if ppa.ok:
                    row = ppa_to_row(label, rtl, ppa)
                    out.write(json.dumps(row) + "\n")
                    n_ok += 1
            except Exception as e:  # noqa: BLE001
                print(f"  skip {label}: {e}", flush=True)
            if i % 50 == 0:
                print(f"  {i}/{len(items)} ({n_ok} ok)", flush=True)
    print(f"wrote {n_ok} rows → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
