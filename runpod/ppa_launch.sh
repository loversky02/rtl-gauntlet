#!/usr/bin/env bash
# Self-contained + SELF-TERMINATING OpenLane PPA data-gen for a RunPod CPU pod (R-B1-full).
#
# Run this on a pod whose IMAGE is the OpenLane 2 image (native `openlane` on PATH — no
# Docker-in-Docker, per the paper). It clones the careset branch, imports the task corpus,
# runs the real Sky130 synth->P&R->STA over the designs, and pushes results/ppa_real.jsonl back
# to a per-pod branch so it is retrievable without pod-log access.
#
# Env (via `runpodctl create pod --env`):
#   RUNPOD_API_KEY  — to self-terminate
#   RUNPOD_POD_ID   — injected by RunPod
#   GH_TOKEN        — repo-scoped PAT, so the pod can push the PPA dataset back
#   PPA_GLOB        — optional; task glob to size (default: self-authored + graded designs)
set -uo pipefail

terminate_self() {
  echo "[ppa] self-terminating pod ${RUNPOD_POD_ID:-?}"
  curl -s "https://api.runpod.io/graphql?api_key=${RUNPOD_API_KEY:-}" \
    -H 'Content-Type: application/json' \
    -d "{\"query\":\"mutation{podTerminate(input:{podId:\\\"${RUNPOD_POD_ID:-}\\\"})}\"}" \
    >/dev/null 2>&1 || true
}
trap terminate_self EXIT
( sleep 21600; terminate_self ) &   # 6 h hard cap (P&R over many designs is slow)

job() {
  set -x
  export DEBIAN_FRONTEND=noninteractive PIP_ROOT_USER_ACTION=ignore
  cd /workspace 2>/dev/null || cd /root
  command -v git >/dev/null 2>&1 || { apt-get update -y && apt-get install -y git; }
  command -v yosys >/dev/null 2>&1 || { apt-get update -y && apt-get install -y iverilog yosys; }
  rm -rf rtl-gauntlet
  git clone --depth 1 -b careset-oracle-revision https://github.com/loversky02/rtl-gauntlet.git
  cd rtl-gauntlet
  git clone --depth 1 https://github.com/NVlabs/verilog-eval.git external/verilog-eval 2>/dev/null || true
  pip install -q -r requirements.txt || true
  python3 scripts/import_veval.py --all 2>/dev/null || python3 scripts/import_veval.py || true
  command -v openlane >/dev/null 2>&1 || { echo "[ppa] ERROR: openlane not on PATH — launch on the OpenLane2 image"; return 3; }
  mkdir -p results
  # Real Sky130 PPA over the corpus (goldens + candidates). --openlane calls native `openlane`.
  # NOTE: gen_ppa_data globs the whole corpus; for the size-graded set (spm/AES/picorv32/ibex)
  # add those designs under tasks/ first and scope corpus() — see docs/C3_PLAN.md.
  python3 scripts/gen_ppa_data.py --openlane --out results/ppa_real.jsonl
  echo "[ppa] rows: $(wc -l < results/ppa_real.jsonl 2>/dev/null || echo 0)"
}

echo "=== PPA_DATAGEN_START ==="
if job; then echo "=== PPA_DATAGEN_DONE ok ==="; else echo "=== PPA_DATAGEN_FAILED rc=$? ==="; fi

# Push the dataset back to a per-pod branch (retrieval without pod-log access).
if [ -n "${GH_TOKEN:-}" ] && [ -f /workspace/rtl-gauntlet/results/ppa_real.jsonl -o -f /root/rtl-gauntlet/results/ppa_real.jsonl ]; then
  cd /workspace/rtl-gauntlet 2>/dev/null || cd /root/rtl-gauntlet
  mkdir -p results/runpod && cp results/ppa_real.jsonl "results/runpod/ppa_real_${RUNPOD_POD_ID:-pod}.jsonl" 2>/dev/null || true
  git config user.email pod@runpod && git config user.name runpod
  git add results/runpod/*.jsonl
  git commit -m "runpod: real Sky130 PPA dataset from ${RUNPOD_POD_ID:-pod}" || true
  git push "https://x-access-token:${GH_TOKEN}@github.com/loversky02/rtl-gauntlet.git" \
    "HEAD:runpod-results-${RUNPOD_POD_ID:-pod}" 2>&1 | tail -3
  echo "[push] PPA dataset on branch runpod-results-${RUNPOD_POD_ID:-pod}"
fi

sleep 300   # keep alive briefly, then the EXIT trap terminates the pod
