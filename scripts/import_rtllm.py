"""Tier-2: import RTLLM (50 designs) as a SECOND public benchmark — escaping the 0/156 power trap.

Each RTLLM leaf dir ships design_description.txt (spec), verified_<name>.v (golden), testbench.v
(visible TB printing "Your Design Passed" on success). We adapt to the repo's task schema:
  - test.sv: the TB with our sentinel injected — the "...Passed..." display is wrapped in
    begin/end and followed by `RTLG_RESULT: PASS` (no sentinel ⇒ sim counts FAIL, the safe default);
  - ref_module.v: empty stub (RTLLM TBs instantiate the DUT directly);
  - top/interface parsed from the golden module header.

After import, the FAIRNESS GATE (paper §3, oracle-independent) is mechanical:
  python3 scripts/run_veval.py --oracle --glob "tasks/rtllm_*"
a task is fair iff its golden passes its own visible TB (and golden-vs-golden must be proven).

  python3 scripts/import_rtllm.py [--src /tmp/rtllm]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re

STUB = "// RTLLM testbenches instantiate the DUT directly; no reference module.\n"


def module_header(src: str) -> tuple[str, str] | None:
    """(top_name, header_text) for the first module in the file."""
    m = re.search(r"\bmodule\s+([A-Za-z_]\w*)\s*(#\s*\([^)]*\)\s*)?\(.*?\)\s*;", src, re.DOTALL)
    if not m:
        return None
    return m.group(1), m.group(0)


def inject_sentinel(tb: str) -> str:
    """Wrap every "...Passed..." display so it also emits the RTLG sentinel (safe in both
    single-statement-if and begin/end contexts)."""
    def repl(m):
        stmt = m.group(0)
        return ("begin " + stmt + ' $display("RTLG_RESULT: PASS"); end')
    out, n = re.subn(r'\$display\("[^"]*Passed[^"]*"\)\s*;', repl, tb)
    return out if n else tb


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="/tmp/rtllm")
    ap.add_argument("--dst", default="tasks")
    args = ap.parse_args()

    goldens = sorted(g for g in glob.glob(os.path.join(args.src, "**", "verified_*.v"), recursive=True)
                     if "_chatgpt" not in g)
    ok = skip = 0
    for g in goldens:
        d = os.path.dirname(g)
        name = os.path.basename(d).replace(" ", "_")
        tb_p, spec_p = os.path.join(d, "testbench.v"), os.path.join(d, "design_description.txt")
        if not (os.path.exists(tb_p) and os.path.exists(spec_p)):
            print(f"skip {name}: missing tb/spec"); skip += 1; continue
        gsrc = open(g, errors="ignore").read()
        hdr = module_header(gsrc)
        if not hdr:
            print(f"skip {name}: no module header"); skip += 1; continue
        top, iface = hdr
        # RTLLM goldens are named `verified_<name>` but the TB instantiates `<name>` (their golden is
        # for equivalence-reference only). Strip the prefix so golden co-simulates with the TB.
        if top.startswith("verified_"):
            bare = top[len("verified_"):]
            gsrc = re.sub(rf"\b{re.escape(top)}\b", bare, gsrc)
            iface = re.sub(rf"\b{re.escape(top)}\b", bare, iface)
            top = bare
        tb = inject_sentinel(open(tb_p, errors="ignore").read())
        if "RTLG_RESULT" not in tb:
            print(f"skip {name}: no Passed-display to hook"); skip += 1; continue
        out = os.path.join(args.dst, f"rtllm_{name}")
        os.makedirs(out, exist_ok=True)
        open(os.path.join(out, "spec.md"), "w").write(
            "# Spec (RTLLM: " + name + ")\n\n" + open(spec_p, errors="ignore").read())
        open(os.path.join(out, "golden.v"), "w").write(gsrc)
        open(os.path.join(out, "test.sv"), "w").write(tb)
        open(os.path.join(out, "ref_module.v"), "w").write(STUB)
        json.dump({"task_id": f"rtllm_{name}", "top": top, "source": "rtllm",
                   "has_reference": True, "interface": iface,
                   "files": {"spec": "spec.md", "golden": "golden.v",
                             "ref_module": "ref_module.v", "test": "test.sv"}},
                  open(os.path.join(out, "task.json"), "w"), indent=2)
        ok += 1
    print(f"imported {ok}/{len(goldens)} RTLLM designs -> tasks/rtllm_*  (skipped {skip})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
