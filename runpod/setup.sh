#!/usr/bin/env bash
# One-command pilot bring-up on a RunPod Linux x86 box (no GPU needed for the
# pilot — it's CPU EDA + routed LLM). Avoids the Apple-Silicon arm64 path (R6).
set -euo pipefail
cd "$(dirname "$0")/.."

SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"

echo "[1/4] EDA tools (iverilog + yosys [+ verilator])"
if ! command -v iverilog >/dev/null 2>&1 || ! command -v yosys >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    $SUDO apt-get update -y
    $SUDO apt-get install -y iverilog yosys verilator
  else
    echo "  ! Install iverilog + yosys manually, or use YosysHQ/oss-cad-suite"
    echo "    (oss-cad-suite also bundles eqy/sby for the stronger formal tier)."
    exit 1
  fi
fi
iverilog -V 2>&1 | head -1 || true
yosys --version || true

echo "[2/4] Python deps"
pip install -r requirements.txt

echo "[3/4] Verify parsers (no EDA needed)"
python scripts/demo_parsers.py

echo "[4/4] Oracle check — baselines, NO LLM (this is the real iverilog+yosys run)"
python scripts/run_pilot.py --task tasks/pilot_gray2bin --baselines

cat <<'EOF'

Expected: honest (golden) passes visible+hidden+formal; dishonest (planted_overfit)
passes visible but FAILS hidden+formal  →  RHG = 0.50, HPR = 0.50.
That confirms the two-tier oracle works end-to-end on real EDA.

Agentic run via 9router:
  export RTLG_BASE_URL=http://<your-9router>/v1
  export RTLG_API_KEY=...           # gateway key
  export RTLG_MODEL=gpt-5.5         # pin the exact id (R20)
  python scripts/run_pilot.py --task tasks/pilot_gray2bin
EOF
