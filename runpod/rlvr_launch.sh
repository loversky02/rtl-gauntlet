#!/usr/bin/env bash
# Self-contained + SELF-TERMINATING RLVR smoke for a RunPod GPU pod.
#
# The pod runs THIS (fetched from GitHub raw at startup). It clones the repo +
# VerilogEval, installs EDA + RL deps, regenerates the task set, runs the 50-step GRPO
# smoke, prints runs/grpo/rhg_curve.jsonl to the pod log, and then ALWAYS terminates the
# pod — on success, on failure, or after a 2.5 h hard cap — so no GPU is ever left billing.
#
# Requires two env vars (passed via `runpodctl create pod --env`):
#   RUNPOD_API_KEY   — to self-terminate via the GraphQL API
#   RUNPOD_POD_ID    — injected automatically by RunPod on every pod
#
# Retrieval: the reward-hacking curve is echoed between RLVR_CURVE_BEGIN/END markers in
# the pod log (`runpodctl pod logs <id>`), so no file transfer is needed.
set -uo pipefail

terminate_self() {
  echo "[launch] self-terminating pod ${RUNPOD_POD_ID:-?}"
  curl -s "https://api.runpod.io/graphql?api_key=${RUNPOD_API_KEY:-}" \
    -H 'Content-Type: application/json' \
    -d "{\"query\":\"mutation{podTerminate(input:{podId:\\\"${RUNPOD_POD_ID:-}\\\"})}\"}" \
    >/dev/null 2>&1 || true
}
trap terminate_self EXIT

# Hard safety net: kill the pod after 2.5 h no matter what the job is doing.
( sleep 9000; terminate_self ) &

job() {
  set -x
  export DEBIAN_FRONTEND=noninteractive PIP_ROOT_USER_ACTION=ignore
  cd /workspace 2>/dev/null || cd /root
  rm -rf rtl-gauntlet
  git clone --depth 1 -b careset-oracle-revision https://github.com/loversky02/rtl-gauntlet.git
  cd rtl-gauntlet
  git clone --depth 1 https://github.com/NVlabs/verilog-eval.git external/verilog-eval
  command -v yosys >/dev/null 2>&1 || { apt-get update -y && apt-get install -y iverilog yosys; }
  pip install -q -r requirements.txt || true
  python -c "import torch, vllm" 2>/dev/null || pip install -q torch==2.5.1 vllm==0.7.3
  pip install -q -r runpod/requirements-rl.txt
  python3 scripts/import_veval.py --all 2>/dev/null || python3 scripts/import_veval.py
  echo "[launch] tasks generated: $(ls tasks 2>/dev/null | grep -c veval)"
  mkdir -p runs/grpo
  # --num-gen 2 keeps 4B GRPO within a 24 GB GPU (LoRA + gradient-checkpointing already on);
  # --num-gen 8 OOMs a 3090/4090. GRPO needs >=2 generations for an advantage.
  python3 scripts/train_grpo.py --model Qwen/Qwen3-4B --glob "tasks/veval_*" --smoke --num-gen 2
}

echo "=== RLVR_SMOKE_START ==="
if job; then echo "=== RLVR_SMOKE_DONE ok ==="; else echo "=== RLVR_SMOKE_FAILED rc=$? ==="; fi
echo "RLVR_CURVE_BEGIN"
cat "$(find / -name rhg_curve.jsonl 2>/dev/null | head -1)" 2>/dev/null || echo "NO_CURVE"
echo "RLVR_CURVE_END"

# Push the curve back to a per-pod branch so it is retrievable WITHOUT pod-log access
# (this runpodctl build has no `pod logs`). Needs a repo-scoped GH_TOKEN via --env.
if [ -n "${GH_TOKEN:-}" ]; then
  cd /workspace/rtl-gauntlet 2>/dev/null || cd /root/rtl-gauntlet 2>/dev/null || true
  CURVE=$(find / -name rhg_curve.jsonl 2>/dev/null | head -1)
  if [ -n "$CURVE" ]; then
    mkdir -p results/runpod && cp "$CURVE" "results/runpod/rhg_curve_${RUNPOD_POD_ID:-pod}.jsonl"
    git config user.email pod@runpod && git config user.name runpod
    git add results/runpod/*.jsonl
    git commit -m "runpod: RLVR rhg_curve from ${RUNPOD_POD_ID:-pod}" || true
    git push "https://x-access-token:${GH_TOKEN}@github.com/loversky02/rtl-gauntlet.git" \
      "HEAD:runpod-results-${RUNPOD_POD_ID:-pod}" 2>&1 | tail -3
    echo "[push] results on branch runpod-results-${RUNPOD_POD_ID:-pod}"
  fi
fi

# Keep the pod alive briefly so the log is retrievable, then the EXIT trap terminates it.
sleep 300
