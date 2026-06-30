"""C3 latency axis — PPA (power/performance/area) data + surrogate interface.

Two PPA sources:
  - `run_openlane(...)`  real synth→P&R→STA via OpenLane/Sky130 (RunPod, slow: minutes).
  - `mock_ppa(...)`      synthetic PPA from RTL features (offline, for pipeline tests).

The agent's slow reward is the ground-truth flow; a surrogate trained on (features → PPA)
gives a fast proxy so the agent can reason under high-latency reward (HORIZON's open problem).
Stdlib only (feature extraction + mock); OpenLane/torch are used only on the GPU pod.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass

_INT = re.compile(r"\[(\d+)\s*:\s*0\]")


@dataclass
class PPAResult:
    area_um2: float
    power_mw: float
    timing_ns: float          # critical-path delay (lower = faster)
    ok: bool
    source: str               # "openlane" | "mock"


def extract_features(rtl_path: str) -> dict:
    """Cheap structural features of an RTL file (regex; no synthesis)."""
    txt = open(rtl_path).read()
    widths = [int(m) for m in _INT.findall(txt)] or [0]
    return {
        "lines": txt.count("\n"),
        "always": len(re.findall(r"\balways\b", txt)),
        "assign": len(re.findall(r"\bassign\b", txt)),
        "case": len(re.findall(r"\bcase\b", txt)),
        "ff": len(re.findall(r"posedge|negedge", txt)),
        "ops": len(re.findall(r"[&|^~]|\+|\-|\*|<<|>>", txt)),
        "max_bits": max(widths),
        "mux": len(re.findall(r"\?", txt)),
    }


def mock_ppa(features: dict) -> PPAResult:
    """Synthetic-but-monotonic PPA so the whole pipeline (data → surrogate → agent)
    can be exercised offline without OpenLane."""
    f = features
    area = 5 * f["ops"] + 18 * f["ff"] + 8 * f["case"] * (f["max_bits"] + 1) + 3 * f["mux"]
    power = 0.04 * area + 0.4 * f["ff"]
    timing = 1.0 + 0.25 * f["ff"] + 0.12 * (f["ops"] ** 0.5)
    return PPAResult(round(area, 2), round(power, 3), round(timing, 3), True, "mock")


def run_openlane(rtl_path: str, top: str, workdir: str, timeout: int = 3600) -> PPAResult:
    """Real PPA via OpenLane (Sky130). Runs on a RunPod CPU box (see runpod/ppa_setup.sh).
    Parses the flow's final metrics JSON. Returns ok=False if the flow fails/missing."""
    os.makedirs(workdir, exist_ok=True)
    cmd = ["bash", "runpod/ppa_setup.sh", "--run", rtl_path, top, workdir]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return PPAResult(0, 0, 0, False, "openlane")
    metrics = os.path.join(workdir, "metrics.json")
    if not os.path.exists(metrics):
        return PPAResult(0, 0, 0, False, "openlane")
    m = json.load(open(metrics))
    return PPAResult(
        area_um2=float(m.get("design__instance__area", 0)),
        power_mw=float(m.get("power__total", 0)) * 1e3,
        timing_ns=float(m.get("timing__setup__ws", 0)) * -1,  # worst slack → delay proxy
        ok=True, source="openlane",
    )


def ppa_to_row(task_id: str, rtl_path: str, ppa: PPAResult) -> dict:
    return {"task": task_id, "features": extract_features(rtl_path), **asdict(ppa)}
