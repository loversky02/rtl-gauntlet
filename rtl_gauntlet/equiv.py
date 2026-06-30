"""Formal equivalence of a candidate RTL against a curated golden, via Yosys.

This is the independent ORACLE for the FORMAL tier (ADR-0001). It is the *tool*,
not the contribution — its job is to permit architectural freedom (any internally
different but functionally identical design passes) while catching designs that
only match the visible test vectors.

Requires `yosys` on PATH → runs inside the CVDP sim image on RunPod.

Interface lock (R16): equivalence needs both designs to expose the SAME top-level
ports. The task spec fixes the I/O; agents may change internals only.
Scale (R5): `equiv_induct` is bounded; on non-termination we report INCONCLUSIVE
rather than a false verdict, and the caller falls back to randomized vectors.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from .schema import (
    FORMAL_CEX,
    FORMAL_INCONCLUSIVE,
    FORMAL_PROVEN,
    FORMAL_TIMEOUT,
)


@dataclass
class EquivResult:
    proven: bool
    status: str          # one of FORMAL_*
    log: str


def build_equiv_script(golden: str, candidate: str, top: str, seq_depth: int = 20) -> str:
    """Yosys script: elaborate each design separately, stash them, then build the
    $equiv miter and prove.

    `design -stash` is required: a plain second `read_verilog` + `hierarchy -top`
    would prune the already-loaded `gold` module (it isn't under the new top).
    `seq_depth` is reserved for future bounded sequential runs; equiv_induct's
    default depth is fine for the small pilot designs.
    """
    return f"""
read_verilog {golden}
hierarchy -top {top}
proc
opt_clean
rename {top} gold
design -stash gold

read_verilog {candidate}
hierarchy -top {top}
proc
opt_clean
rename {top} gate
design -stash gate

design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate equiv
hierarchy -top equiv
opt_clean
equiv_simple
equiv_induct
equiv_status -assert
""".strip()


def parse_equiv(log: str, returncode: int, timed_out: bool) -> tuple[bool, str]:
    if timed_out:
        return False, FORMAL_TIMEOUT
    low = log.lower()
    # equiv_status -assert exits 0 iff every $equiv cell was proven. The textual
    # "Equivalence successfully proven!" is suppressed under -q, so trust the exit
    # code as the primary signal.
    if returncode == 0 or "equivalence successfully proven" in low:
        return True, FORMAL_PROVEN
    if "unproven" in low:          # nonzero + unproven cells → genuine mismatch
        return False, FORMAL_CEX
    # syntax error, interface mismatch, unmapped state → not a real CEX
    return False, FORMAL_INCONCLUSIVE


def run_equiv(
    golden: str,
    candidate: str,
    top: str,
    workdir: str,
    seq_depth: int = 20,
    timeout: int = 300,
) -> EquivResult:
    os.makedirs(workdir, exist_ok=True)
    script = build_equiv_script(golden, candidate, top, seq_depth)
    script_path = os.path.join(workdir, "equiv.ys")
    with open(script_path, "w") as f:
        f.write(script + "\n")
    try:
        r = subprocess.run(["yosys", "-s", script_path],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        proven, status = parse_equiv("", 124, True)
        return EquivResult(proven, status, "yosys timeout")
    log = r.stdout + r.stderr
    proven, status = parse_equiv(log, r.returncode, False)
    return EquivResult(proven, status, log)
