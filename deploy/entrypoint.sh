#!/usr/bin/env bash
# Railway worker: download the PDK once, run PPA data-gen, exit. Data → /data volume.
set -euo pipefail
cd /app

export PDK_ROOT="${PDK_ROOT:-/app/.ciel}"
mkdir -p /data

echo "[1/2] Sky130 PDK (ciel)"
ciel enable --pdk-root "$PDK_ROOT" 2>/dev/null || openlane --version || true

echo "[2/2] PPA data-gen (real OpenLane flow per design)"
# LIMIT controls how many designs to run (cost control on a metered box).
python3 scripts/gen_ppa_data.py --openlane --out /data/ppa_dataset.jsonl

echo "done → /data/ppa_dataset.jsonl ($(wc -l < /data/ppa_dataset.jsonl) rows)"
