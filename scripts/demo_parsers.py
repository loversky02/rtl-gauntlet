"""Verify the sim + formal output parsers WITHOUT any EDA tools (runs on the Mac).

The real iverilog/yosys runs happen on RunPod; here we lock down the parsing
logic against representative tool output so the oracle's verdict mapping is
trustworthy before we ever spin a container.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rtl_gauntlet.equiv import parse_equiv  # noqa: E402
from rtl_gauntlet.schema import FORMAL_CEX, FORMAL_INCONCLUSIVE, FORMAL_PROVEN, FORMAL_TIMEOUT  # noqa: E402
from rtl_gauntlet.sim import parse_sim  # noqa: E402

# --- simulation parser ---
SIM_CASES = [
    ("...\nRTLG_RESULT: PASS\n", True),
    ("RTLG_RESULT: FAIL (gray=0011 got=0000 exp=0010)\n", False),
    ("vvp: error: ...segfault...\n", False),          # no sentinel → fail
    ("", False),                                       # empty → fail
]

# --- formal parser: (log, returncode, timed_out) -> status ---
EQUIV_CASES = [
    ("Equivalence successfully proven!\n", 0, False, FORMAL_PROVEN),
    ("Found 0 unproven $equiv cells in 'equiv': SUCCESS!\n", 0, False, FORMAL_PROVEN),
    ("Found 2 unproven $equiv cells in 'equiv':\nERROR: equiv_status\n", 1, False, FORMAL_CEX),
    ("ERROR: Module 'gate' has different ports\n", 1, False, FORMAL_INCONCLUSIVE),
    ("", 124, True, FORMAL_TIMEOUT),
]


def main() -> int:
    print("Parser verification (no EDA tools needed)\n")

    for log, want in SIM_CASES:
        got, note = parse_sim(log)
        assert got == want, f"sim parse {want=} {got=} for {log!r}"
        print(f"  ✓ sim   {str(got):5s}  [{note}]")

    for log, rc, to, want in EQUIV_CASES:
        ok, status = parse_equiv(log, rc, to)
        assert status == want, f"equiv parse {want=} {status=} for {log!r}"
        print(f"  ✓ formal {status:13s} proven={ok}")

    print("\n  ✓ all parser cases hold — verdict mapping is correct.")
    print("  Next: run the real flow on RunPod with `bash runpod/setup.sh`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
