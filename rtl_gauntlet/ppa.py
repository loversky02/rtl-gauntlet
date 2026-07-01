"""C3 latency axis — PPA (power/performance/area) data + surrogate interface.

Two PPA sources:
  - `run_openlane(...)`  real synth→P&R→STA via OpenLane/Sky130 (RunPod, slow: minutes).
  - `mock_ppa(...)`      synthetic PPA from RTL features (offline, for pipeline tests).

The agent's slow reward is the ground-truth flow; a surrogate trained on (features → PPA)
gives a fast proxy so the agent can reason under high-latency reward (HORIZON's open problem).
Stdlib only (feature extraction + mock); OpenLane/torch are used only on the GPU pod.
"""

from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass

_INT = re.compile(r"\[(\d+)\s*:\s*0\]")
_CLK = re.compile(r"\binput\b[^;]*?\b(clk|clock|clk_i|clock_i)\b")


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


def _clock_port(rtl_text: str) -> str | None:
    m = _CLK.search(rtl_text)
    return m.group(1) if m else None


def run_openlane(rtl_path: str, top: str, workdir: str, timeout: int = 3600,
                 config_extra: dict | None = None) -> PPAResult:
    """Real PPA via OpenLane 2 (Sky130). Expects to run INSIDE the openlane2 image
    (tools present → no Docker-in-Docker); on Railway the container is that image.
    Generates a per-design config (clock only if the RTL has a clock port — risk R-config),
    runs `openlane config.json`, and parses the flow's final metrics. ok=False on failure.
    `config_extra` overrides/adds config keys (e.g. a SYNTH_STRATEGY, for rank-stability sweeps)."""
    os.makedirs(os.path.join(workdir, "src"), exist_ok=True)
    shutil.copy(rtl_path, os.path.join(workdir, "src", "design.v"))
    cfg = {"DESIGN_NAME": top, "VERILOG_FILES": "dir::src/*.v", "PDK": "sky130A",
           "CLOCK_PERIOD": 10}             # OpenLane needs a period even for comb paths
    clk = _clock_port(open(rtl_path).read())
    if clk:
        cfg["CLOCK_PORT"] = clk
    # else combinational: no CLOCK_PORT → OpenLane runs a comb flow (area/power; timing N/A)
    if config_extra:
        cfg.update(config_extra)
    json.dump(cfg, open(os.path.join(workdir, "config.json"), "w"))
    try:
        subprocess.run(["openlane", "config.json"], cwd=workdir,
                       capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return PPAResult(0, 0, 0, False, "openlane")

    found = (glob.glob(os.path.join(workdir, "runs", "*", "final", "metrics.json"))
             or glob.glob(os.path.join(workdir, "runs", "*", "**", "metrics.json"), recursive=True))
    if not found:
        return PPAResult(0, 0, 0, False, "openlane")
    m = json.load(open(sorted(found)[-1]))
    return PPAResult(
        area_um2=float(m.get("design__instance__area", m.get("design__core__area", 0)) or 0),
        power_mw=float(m.get("power__total", 0) or 0) * 1e3,
        timing_ns=-float(m.get("timing__setup__ws", 0) or 0),   # worst slack → delay proxy
        ok=True, source="openlane",
    )


def ppa_to_row(task_id: str, rtl_path: str, ppa: PPAResult) -> dict:
    return {"task": task_id, "features": extract_features(rtl_path), **asdict(ppa)}
