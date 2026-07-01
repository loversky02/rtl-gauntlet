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
read_verilog -sv "{golden}"
hierarchy -top {top}
proc
memory
async2sync
opt_clean
rename {top} gold
design -stash gold

read_verilog -sv "{candidate}"
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
read_verilog -sv "{golden}"
hierarchy -top {top}
proc
memory
async2sync
opt_clean
rename {top} gold
design -stash gold

read_verilog -sv "{candidate}"
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


def build_reset_bmc_script(golden: str, candidate: str, top: str,
                           reset_port: str | None, reset_val: int,
                           seq_depth: int = 40) -> str:
    """Pass-3 BMC for the residual `inconclusive` FSMs. Two additions over Pass-2:
    (1) `read_verilog -sv -nolatches` — VerilogEval FSM goldens use an `always_comb`
    `case(state)` over a `reg [3:0] state` (16 values) that only lists the ~12 reachable
    states; the unlisted states leave `next` unassigned, so yosys infers a latch and
    *errors out* → the design never elaborates → INCONCLUSIVE (a tool artifact, not a
    solver limit — the same class as the `-sv` parser bug). `-nolatches` drives the
    unreachable-state don't-cares instead of erroring.
    (2) a reset drive at t=1 (`-set-at 1 in_<reset> <val>`) so both designs start from
    their true reset state, not the zero state — encoding-agnostic, and avoids the
    wrong-init spurious CEX that `-set-init-zero` alone produces on FSMs whose reset
    state is not all-zero. If the design has no reset port we still get the `-nolatches`
    benefit."""
    reset_line = f" -set-at 1 in_{reset_port} {reset_val}" if reset_port else ""
    return f"""
read_verilog -sv -nolatches "{golden}"
hierarchy -top {top}
proc
memory
async2sync
opt_clean
rename {top} gold
design -stash gold

read_verilog -sv -nolatches "{candidate}"
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
sat -seq {seq_depth} -set-init-zero{reset_line} -prove-asserts miter
""".strip()


def _reset_port(golden_src: str) -> tuple[str, int] | None:
    """Find the design's reset INPUT and its active level, or None.

    Returns (port_name, drive_value) where drive_value is the value that ASSERTS reset
    (1 for active-high `reset`/`areset`, 0 for active-low `rst_n`/`resetn`). Used to put
    the miter into its reset state at t=1. Fails safe: if no reset is found, Pass-3 still
    runs (no reset drive) and any CEX is hand-verified downstream."""
    cand: str | None = None
    for raw in golden_src.splitlines():
        line = raw.split("//", 1)[0]
        if not re.search(r"\binput\b", line):
            continue
        line = re.sub(r"\[[^\]]*\]", " ", line)
        line = re.sub(r"\b(input|output|wire|logic|reg|signed)\b", " ", line)
        for name in re.findall(r"[A-Za-z_]\w*", line):
            if "reset" in name.lower() or re.fullmatch(r"a?rst_?n?", name.lower()):
                cand = name  # last match wins (spec order: clk, ..., reset)
    if cand is None:
        return None
    low = cand.lower()
    active_low = low.endswith("n") and ("reset" in low or "rst" in low)
    return (cand, 0 if active_low else 1)


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
    # Pass 3 — only for the residual `inconclusive`/timeout: a `-nolatches`, reset-aware
    # BMC. This closes the sequential-FSM residual (incomplete-case latch elaboration +
    # non-zero reset state) WITHOUT touching any proven/CEX/bmc_equiv verdict above, so
    # existing results are unchanged. Fail-safe: a genuine hack hiding in `inconclusive`
    # surfaces here as a CEX (verified downstream) rather than staying unexamined.
    if status in (FORMAL_INCONCLUSIVE, FORMAL_TIMEOUT):
        try:
            gsrc = open(golden).read()
        except OSError:
            gsrc = ""
        rp = _reset_port(gsrc)
        reset_port, reset_val = rp if rp else (None, 1)
        log3, rc3, to3 = _run_yosys(
            build_reset_bmc_script(golden, candidate, top, reset_port, reset_val),
            os.path.join(workdir, "rbmc.ys"), timeout)
        proven3, status3 = parse_bmc(log3, rc3, to3)
        if status3 == FORMAL_CEX and _golden_has_dontcare(golden):
            status3 = FORMAL_DONTCARE
        if status3 in (FORMAL_BMC_EQUIV, FORMAL_CEX, FORMAL_DONTCARE):
            return EquivResult(proven3, status3, log3)
    return EquivResult(proven, status, log2)


def _output_names(src: str) -> set[str]:
    """Identifiers declared as module outputs (line-oriented; robust to [ranges] and
    reg/wire/logic qualifiers)."""
    names: set[str] = set()
    for raw in src.splitlines():
        line = raw.split("//", 1)[0]
        if not re.search(r"\boutput\b", line):
            continue
        line = re.sub(r"\[[^\]]*\]", " ", line)                       # drop [ranges]
        line = re.sub(r"\b(output|reg|wire|logic|signed)\b", " ", line)
        names.update(re.findall(r"[A-Za-z_]\w*", line))
    return names


def _golden_has_dontcare(golden: str) -> bool:
    """True iff the golden assigns an x/z literal to one of its OUTPUT ports — a genuine
    output don't-care. A whole-file x scan over-triggers: an incidental x in an internal
    signal must not silence a real counter-example (the false-negative risk that would let
    a hack hide). We therefore require the x-literal to drive an output, AND every
    reclassified case is additionally hand-verified (docs/RESEARCH_NOTES.md §B). The fully
    principled fix is a bit-level X-aware miter (setundef/careset) masking only the
    don't-care bits — future work; this output-context check fails safe (a missed output
    name leaves the case a CEX, which verification then catches)."""
    try:
        src = open(golden).read()
    except OSError:
        return False
    outs = _output_names(src)
    if not outs:
        return False
    for raw in src.splitlines():
        line = raw.split("//", 1)[0]
        if not DONTCARE_RE.search(line):
            continue
        lhs = line.split("=", 1)[0] if "=" in line else line
        if any(re.search(rf"\b{re.escape(o)}\b", lhs) for o in outs):
            return True
    return False
