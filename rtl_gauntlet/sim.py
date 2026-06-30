"""Run a Verilog testbench (Icarus) and decide pass/fail deterministically.

Convention: our testbenches print a sentinel line `RTLG_RESULT: PASS` or
`RTLG_RESULT: FAIL` exactly once. This removes the usual fragile log-scraping —
no sentinel (compile crash, $fatal, timeout) is treated as FAIL.

Requires `iverilog` + `vvp` on PATH → runs inside the CVDP sim image on RunPod,
NOT on the host Mac.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

SENTINEL_PASS = "RTLG_RESULT: PASS"
SENTINEL_FAIL = "RTLG_RESULT: FAIL"


@dataclass
class SimResult:
    passed: bool
    log: str
    returncode: int
    note: str = ""


def parse_sim(log: str) -> tuple[bool, str]:
    """(passed, note) from a simulation log using the sentinel convention."""
    if SENTINEL_PASS in log:
        return True, "sentinel:pass"
    if SENTINEL_FAIL in log:
        return False, "sentinel:fail"
    return False, "no-sentinel (crash/timeout/missing $display)"


def run_iverilog(
    rtl_files: list[str],
    tb_file: str,
    workdir: str,
    timeout: int = 120,
) -> SimResult:
    """Compile rtl_files + tb_file with Icarus, run, and classify the result."""
    os.makedirs(workdir, exist_ok=True)
    out = os.path.join(workdir, "sim.vvp")
    compile_cmd = ["iverilog", "-g2012", "-o", out, *rtl_files, tb_file]
    try:
        c = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return SimResult(False, "compile timeout", 124, "timeout")
    if c.returncode != 0:
        return SimResult(False, "COMPILE ERROR\n" + c.stdout + c.stderr,
                         c.returncode, "compile-error")
    try:
        r = subprocess.run(["vvp", out], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return SimResult(False, "run timeout", 124, "timeout")
    log = r.stdout + r.stderr
    passed, note = parse_sim(log)
    return SimResult(passed, log, r.returncode, note)
