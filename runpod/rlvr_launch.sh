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
  # Prereqs: launch on a base image whose CMD is bash (e.g. nvidia/cuda:*-devel), NOT runpod/pytorch
  # (its entrypoint hijacks --args, so the pod idles at 0% util). A bare CUDA image has no git/python.
  command -v git >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1 || \
    { apt-get update -y && apt-get install -y --no-install-recommends git curl ca-certificates python3 python3-pip; }
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
  # --num-gen 2 keeps 4B GRPO within a 24 GB GPU (LoRA + gradient-checkpointing already on).
  # --sft-first: SFT cold-start on (spec -> golden) so the sparse GRPO reward has a non-zero
  # advantage (else it collapses, DAPO arXiv:2503.14476). GRPO needs >=2 generations.
  python3 scripts/train_grpo.py --model Qwen/Qwen3-4B --glob "tasks/veval_*" --smoke --num-gen 2 --sft-first
}

echo "=== RLVR_SMOKE_START ==="
job > /tmp/rlvr-log.txt 2>&1; RC=$?
echo "=== RLVR_SMOKE $([ "$RC" = 0 ] && echo DONE_ok || echo FAILED_rc=$RC) ==="
tail -60 /tmp/rlvr-log.txt

# Push the LOG (ALWAYS — so failures are diagnosable without pod-log access) + the curve (if any)
# to a per-pod branch. Needs a repo-scoped GH_TOKEN via --env.
if [ -n "${GH_TOKEN:-}" ]; then
  cd /workspace/rtl-gauntlet 2>/dev/null || cd /root/rtl-gauntlet 2>/dev/null || \
    { cd /tmp && git clone --depth 1 -b careset-oracle-revision \
      https://github.com/loversky02/rtl-gauntlet.git rgpush && cd rgpush; }
  mkdir -p results/runpod
  cp /tmp/rlvr-log.txt "results/runpod/rlvr_log_${RUNPOD_POD_ID:-pod}.txt" 2>/dev/null || true
  CURVE=$(find / -name rhg_curve.jsonl 2>/dev/null | head -1)
  [ -n "$CURVE" ] && cp "$CURVE" "results/runpod/rhg_curve_${RUNPOD_POD_ID:-pod}.jsonl"
  git config user.email pod@runpod && git config user.name runpod
  git add results/runpod/* 2>/dev/null
  git commit -m "runpod: RLVR log+curve from ${RUNPOD_POD_ID:-pod} (rc=$RC)" || true
  git push "https://x-access-token:${GH_TOKEN}@github.com/loversky02/rtl-gauntlet.git" \
    "HEAD:runpod-results-${RUNPOD_POD_ID:-pod}" 2>&1 | tail -3
  echo "[push] results+log on branch runpod-results-${RUNPOD_POD_ID:-pod}"
fi

sleep 120   # brief keepalive, then the EXIT trap terminates the pod
