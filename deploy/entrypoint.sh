#!/usr/bin/env bash
# Railway worker: download PDK once, run real OpenLane PPA per design, print the
# dataset to the logs (so it can be read without a volume), then exit.
set -uo pipefail
cd /app
export PDK_ROOT="${PDK_ROOT:-/app/.ciel}"
mkdir -p /data
PY="$(command -v python3 || command -v python)"

echo "[1/3] python = $PY ; openlane = $(command -v openlane || echo MISSING)"
echo "[2/3] Sky130 PDK (ciel)"
ciel enable --pdk-root "$PDK_ROOT" 2>&1 | tail -3 || true

echo "[3/3] PPA data-gen (real OpenLane flow; PPA_GLOB designs x PPA_STRATEGIES — P&R is slow)"
"$PY" scripts/gen_ppa_data.py --openlane --out /data/ppa_dataset.jsonl \
  --glob "${PPA_GLOB:-tasks/*}" --strategies "${PPA_STRATEGIES:-}" --limit "${PPA_LIMIT:-0}" || true

echo "=====BEGIN ppa_dataset.jsonl====="
cat /data/ppa_dataset.jsonl 2>/dev/null || echo "(no rows)"
echo "=====END ppa_dataset.jsonl====="
