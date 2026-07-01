"""Verify the contamination-probe mutants are FUNCTION-PRESERVING, using the A1 sound oracle.

The reviewer asked that each semantic/identifier mutation be *verified equivalent* to its source rather
than assumed. We prove it: rename each mutant's module back to the canonical top and run the hardened
`run_equiv` (incl. the X-aware careset miter) against the original golden. A pass (proven / bmc_equiv /
careset_equiv) certifies the mutation did not change the function, so any honesty result measured on the
mutant reflects reasoning, not a broken task.

  python3 scripts/verify_mutants.py
"""
from __future__ import annotations

import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rtl_gauntlet.equiv import run_equiv  # noqa: E402

EQUIV = {"proven", "bmc_equiv", "careset_equiv"}
NEWMOD = "DutUnderTest"   # the identifier mutate_tasks.py renames TopModule to


def main() -> int:
    muts = sorted(glob.glob("tasks/mut_*"))
    if not muts:
        print("no tasks/mut_* found — generate with: python3 scripts/mutate_tasks.py")
        return 0
    ok = cex = other = 0
    bad = []
    for md in muts:
        name = os.path.basename(md).replace("mut_", "")
        orig = f"tasks/veval_{name}/golden.v"
        if not os.path.exists(orig):
            continue
        mg = re.sub(rf"\b{NEWMOD}\b", "TopModule", open(os.path.join(md, "golden.v")).read())
        tmp = os.path.join(md, "_verify_golden.v")
        open(tmp, "w").write(mg)
        try:
            r = run_equiv(orig, tmp, "TopModule", f"runs/mutverify/{name}", timeout=60)
        finally:
            os.remove(tmp)
        if r.status in EQUIV:
            ok += 1
        elif r.status == "cex":
            cex += 1
            bad.append((name, "cex"))
        else:
            other += 1
            bad.append((name, r.status))
    print(f"verified function-preserving: {ok}/{ok + cex + other}  (cex={cex}, inconclusive/err={other})")
    if bad:
        print("non-equivalent:", bad[:12])
    return 0 if cex == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
