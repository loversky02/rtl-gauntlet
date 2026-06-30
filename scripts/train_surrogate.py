"""Train + evaluate the PPA surrogate on results/ppa_dataset.jsonl.

Deterministic 80/20 split; reports holdout Pearson r per PPA target (faithfulness).
Offline (pure-python). The production GNN trains on GPU — see docs/C3_PLAN.md.

  python scripts/gen_ppa_data.py && python scripts/train_surrogate.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rtl_gauntlet.surrogate import pearson, predict, ridge_fit  # noqa: E402

TARGETS = ["area_um2", "power_mw", "timing_ns"]


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "results/ppa_dataset.jsonl"
    rows = [json.loads(ln) for ln in open(path)]
    train = [r for i, r in enumerate(rows) if i % 5 != 0]
    hold = [r for i, r in enumerate(rows) if i % 5 == 0]
    print(f"PPA surrogate: {len(rows)} designs ({len(train)} train / {len(hold)} holdout)\n")
    for t in TARGETS:
        w = ridge_fit(train, t, lam=1.0)
        pred = [predict(w, r["features"]) for r in hold]
        true = [r[t] for r in hold]
        print(f"  {t:11s} holdout Pearson r = {pearson(pred, true):.3f}")
    print("\n  (mock PPA → high r expected; validates data→surrogate→eval loop offline.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
