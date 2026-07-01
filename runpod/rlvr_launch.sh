#!/usr/bin/env bash
# Self-contained + SELF-TERMINATING RLVR smoke for a RunPod GPU pod.
#
# Launch pattern (IMPORTANT):
#   - Create the pod via the RunPod API with `dockerArgs` (runpodctl --args gets hijacked by the
#     runpod/pytorch entrypoint -> the pod idles at 0% util and nothing ever runs).
#   - dockerArgs must DOWNLOAD this script to a file then execute it:
#       bash -c 'curl -sL <raw-url> -o /tmp/l.sh && bash /tmp/l.sh'
#     NOT `curl | bash` — commands inside a piped script can swallow the remaining script from
#     stdin, truncating it mid-run (the silent-death failure mode we hit).
#
# Env (via API `env`): RUNPOD_API_KEY (self-terminate), GH_TOKEN (push results),
# RUNPOD_POD_ID (injected by RunPod).
#
# Retrieval: a HEARTBEAT pushes /tmp/rlvr-log.txt (+ the RHG curve when it exists) to the branch
# runpod-results-<pod-id> every 5 min, and again on exit — so even a hang or crash is diagnosable
# with no pod-log access. The watchdog (2.5 h) also pushes before terminating.
set -uo pipefail

PODTAG="${RUNPOD_POD_ID:-pod}"
touch /tmp/rlvr-log.txt

push_log() {  # commit+push the current log (+curve if present); never fails the caller
  [ -z "${GH_TOKEN:-}" ] && return 0
  (
    set +e
    cd /tmp
    if [ ! -d hbpush/.git ]; then
      git clone --quiet --depth 1 -b careset-oracle-revision \
        "https://x-access-token:${GH_TOKEN}@github.com/loversky02/rtl-gauntlet.git" hbpush \
        >/dev/null 2>&1 || exit 0
      cd hbpush && git config user.email pod@runpod && git config user.name runpod && cd ..
    fi
    cd /tmp/hbpush || exit 0
    mkdir -p results/runpod
    cp /tmp/rlvr-log.txt "results/runpod/rlvr_log_${PODTAG}.txt" 2>/dev/null
    CURVE=$(find /workspace /root -name rhg_curve.jsonl 2>/dev/null | head -1)
    [ -n "$CURVE" ] && cp "$CURVE" "results/runpod/rhg_curve_${PODTAG}.jsonl"
    git add results/runpod >/dev/null 2>&1
    git commit -q -m "runpod ${PODTAG}: log/curve $(date -u +%FT%TZ)" >/dev/null 2>&1
    git push -q origin "HEAD:runpod-results-${PODTAG}" >/dev/null 2>&1
  ) || true
}

terminate_self() {
  echo "[launch] final push + self-terminate ${PODTAG}" >> /tmp/rlvr-log.txt
  push_log
  curl -s "https://api.runpod.io/graphql?api_key=${RUNPOD_API_KEY:-}" \
    -H 'Content-Type: application/json' \
    -d "{\"query\":\"mutation{podTerminate(input:{podId:\\\"${RUNPOD_POD_ID:-}\\\"})}\"}" \
    >/dev/null 2>&1 || true
}
trap terminate_self EXIT

# Watchdog: after 2.5 h, push the log THEN kill the pod (never die silently).
( sleep 9000; terminate_self ) &
# Heartbeat: push the growing log every 5 min so a hang is visible in the result branch.
( while true; do sleep 300; push_log; done ) &

job() {
  set -x
  export DEBIAN_FRONTEND=noninteractive PIP_ROOT_USER_ACTION=ignore
  # Prereqs for a bare image (nvidia/cuda:*-devel has no git/python).
  command -v git >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1 || \
    { apt-get update -y && apt-get install -y --no-install-recommends git curl ca-certificates python3 python3-pip; }
  cd /workspace 2>/dev/null || cd /root
  rm -rf rtl-gauntlet
  git clone --depth 1 -b careset-oracle-revision https://github.com/loversky02/rtl-gauntlet.git
  cd rtl-gauntlet
  git clone --depth 1 https://github.com/NVlabs/verilog-eval.git external/verilog-eval
  command -v yosys >/dev/null 2>&1 || { apt-get update -y && apt-get install -y iverilog yosys; }
  pip install -q -r requirements.txt || true
  python3 -c "import torch" 2>/dev/null || pip install -q torch==2.5.1
  pip install -q -r runpod/requirements-rl.txt
  python3 scripts/import_veval.py --all 2>/dev/null || python3 scripts/import_veval.py
  echo "[launch] tasks generated: $(ls tasks 2>/dev/null | grep -c veval)"
  mkdir -p runs/grpo
  # --num-gen 2 keeps 4B GRPO within 24 GB (LoRA + gradient-checkpointing already on).
  # --sft-first: SFT cold-start so the sparse GRPO reward has non-zero advantage (DAPO).
  python3 scripts/train_grpo.py --model Qwen/Qwen3-4B --glob "tasks/veval_*" --smoke --num-gen 2 --sft-first
}

echo "=== RLVR_SMOKE_START $(date -u +%FT%TZ) ===" >> /tmp/rlvr-log.txt
push_log                                  # early heartbeat: proves the launcher started
job </dev/null >> /tmp/rlvr-log.txt 2>&1; RC=$?
echo "=== RLVR_SMOKE $([ "$RC" = 0 ] && echo DONE_ok || echo FAILED_rc=$RC) ===" >> /tmp/rlvr-log.txt
push_log                                  # final result push (log + curve)
sleep 60                                  # brief keepalive, then the EXIT trap terminates the pod
