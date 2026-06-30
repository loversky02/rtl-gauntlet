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
import re
import subprocess
from dataclasses import dataclass

from .schema import (
    FORMAL_BMC_EQUIV,
    FORMAL_CEX,
    FORMAL_DONTCARE,
    FORMAL_INCONCLUSIVE,
    FORMAL_PROVEN,
    FORMAL_TIMEOUT,
)

# A Verilog literal containing an x/z (don't-care), e.g. 1'bx, 4'bxxxx, 'x.
DONTCARE_RE = re.compile(r"'[bodhBODH]?[0-9a-fA-F_xXzZ]*[xXzZ]")


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
read_verilog -sv {golden}
hierarchy -top {top}
proc
memory
async2sync
opt_clean
rename {top} gold
design -stash gold

read_verilog -sv {candidate}
hierarchy -top {top}
proc
memory
async2sync
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


def build_bmc_script(golden: str, candidate: str, top: str, seq_depth: int = 20) -> str:
    """Bounded miter+SAT: compares the I/O sequences directly, so it is robust to
    different internal state ENCODINGS (vector vs. scalars) that defeat equiv_induct.
    `-set-init-zero` assumes both designs start from the same (zero) state — the
    sensible assumption for matched-spec designs. No model ⇒ no divergence within
    `seq_depth` cycles; a model ⇒ a concrete, trustworthy counter-example.
    """
    return f"""
read_verilog -sv {golden}
hierarchy -top {top}
proc
memory
async2sync
opt_clean
rename {top} gold
design -stash gold

read_verilog -sv {candidate}
hierarchy -top {top}
proc
memory
async2sync
opt_clean
rename {top} gate
design -stash gate

design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
miter -equiv -flatten -make_assert gold gate miter
hierarchy -top miter
opt_clean
sat -seq {seq_depth} -prove-asserts -set-init-zero miter
""".strip()


def parse_bmc(log: str, returncode: int, timed_out: bool) -> tuple[bool, str]:
    if timed_out:
        return False, FORMAL_TIMEOUT
    low = log.lower()
    if "no model found" in low:        # asserts held for all checked depths
        return True, FORMAL_BMC_EQUIV
    if "model found" in low:           # a real input sequence diverges
        return False, FORMAL_CEX
    return False, FORMAL_INCONCLUSIVE


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


def _run_yosys(script: str, path: str, timeout: int) -> tuple[str, int, bool]:
    with open(path, "w") as f:
        f.write(script + "\n")
    try:
        r = subprocess.run(["yosys", "-s", path], capture_output=True, text=True,
                           timeout=timeout)
        return r.stdout + r.stderr, r.returncode, False
    except subprocess.TimeoutExpired:
        return "yosys timeout", 124, True


def run_equiv(
    golden: str,
    candidate: str,
    top: str,
    workdir: str,
    seq_depth: int = 20,
    timeout: int = 300,
) -> EquivResult:
    """Two-pass: a full equivalence proof, then a bounded miter+SAT fallback that
    is robust to differing state encodings/inits (the deeper false-CEX class)."""
    os.makedirs(workdir, exist_ok=True)
    # Pass 1 — full proof; strongest verdict when it succeeds.
    log1, rc1, to1 = _run_yosys(build_equiv_script(golden, candidate, top, seq_depth),
                                os.path.join(workdir, "equiv.ys"), timeout)
    _, status = parse_equiv(log1, rc1, to1)
    if status == FORMAL_PROVEN:
        return EquivResult(True, FORMAL_PROVEN, log1)
    # Pass 2 — bounded miter+SAT (encoding-agnostic; a model is a real CEX).
    log2, rc2, to2 = _run_yosys(build_bmc_script(golden, candidate, top, seq_depth),
                                os.path.join(workdir, "bmc.ys"), timeout)
    proven, status = parse_bmc(log2, rc2, to2)
    if status == FORMAL_CEX and _golden_has_dontcare(golden):
        # golden x don't-care → a CEX is untrustworthy; don't claim disproof (not RHG).
        status = FORMAL_DONTCARE
    return EquivResult(proven, status, log2)


def _golden_has_dontcare(golden: str) -> bool:
    try:
        with open(golden) as f:
            return DONTCARE_RE.search(f.read()) is not None
    except OSError:
        return False
