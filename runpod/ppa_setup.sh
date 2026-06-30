#!/usr/bin/env bash
# C3 PPA flow on a RunPod box. Two uses:
#   bash runpod/ppa_setup.sh              # install OpenLane 2 + Sky130 (one-time)
#   bash runpod/ppa_setup.sh --run RTL TOP WORKDIR   # synth->P&R->STA one design
#
# GPU is NOT needed here (this is CPU EDA). The GPU is only for training the surrogate
# (scripts/train_surrogate.py / a GNN) — spin a cheap A4000/A5000 up for ~1h then tear down.
set -euo pipefail
cd "$(dirname "$0")/.."

install() {
  python3 -m pip install --upgrade openlane    # OpenLane 2 (pulls Sky130 PDK via volare)
  python3 -c "import volare; volare.enable" 2>/dev/null || true
  echo "OpenLane 2 installed. (Tools come via its container runtime.)"
}

run_one() {
  local rtl="$1" top="$2" wd="$3"
  mkdir -p "$wd"
  # minimal OpenLane 2 config for a single RTL file
  cat > "$wd/config.json" <<EOF
{ "DESIGN_NAME": "$top",
  "VERILOG_FILES": "$(realpath "$rtl")",
  "CLOCK_PORT": "clk", "CLOCK_PERIOD": 10,
  "PDK": "sky130A" }
EOF
  # run the flow; on success copy the final metrics where run_openlane() expects them
  ( cd "$wd" && python3 -m openlane --dockerized config.json ) || true
  local m
  m=$(find "$wd" -name "metrics.json" -path "*final*" | head -1 || true)
  [ -n "$m" ] && cp "$m" "$wd/metrics.json" || echo "{}" > "$wd/metrics.json"
}

case "${1:-install}" in
  --run) shift; run_one "$@" ;;
  *)     install ;;
esac
