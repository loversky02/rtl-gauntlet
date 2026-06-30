#!/usr/bin/env bash
# RLVR smoke on a RunPod GPU pod (A100/H100, x86_64, CUDA 12.x). Trains Qwen3-4B with
# GRPO on the VISIBLE-test reward and audits the reward-hacking gap (RHG) via the
# withheld hidden+formal oracle. See docs/RLVR.md.
set -euo pipefail
cd "$(dirname "$0")/.."
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"

echo "[1/4] EDA tools (iverilog + yosys) — the withheld oracle runs on CPU"
if ! command -v iverilog >/dev/null 2>&1 || ! command -v yosys >/dev/null 2>&1; then
  $SUDO apt-get update -y && $SUDO apt-get install -y iverilog yosys
fi
iverilog -V 2>&1 | head -1 || true
yosys --version | head -1 || true

echo "[2/4] Python: repo + RL deps (pinned transformers 4.51 / trl 0.17)"
pip install -r requirements.txt
# Install torch+vllm matching THIS pod's CUDA first if the image lacks them:
python -c "import torch, vllm" 2>/dev/null || pip install torch==2.5.1 vllm==0.7.3
pip install -r runpod/requirements-rl.txt

echo "[3/4] Build the task set (VerilogEval-derived; visible TB = reward, hidden+formal = audit)"
python3 scripts/import_veval.py --all 2>/dev/null || python3 scripts/import_veval.py

echo "[4/4] SMOKE — 50 steps, audit every 25, 12 held-out tasks (~30-45 min incl. model download)"
python3 scripts/train_grpo.py --model Qwen/Qwen3-4B --glob "tasks/veval_*" --smoke

cat <<'EOF'

Done. RHG curve -> runs/grpo/rhg_curve.jsonl  (one JSON line per audit checkpoint):
  visible_pass_rate vs formal_pass_rate vs step ;  RHG = visible - formal.

Reading it:
  RHG flat ~0, honest_rate rising   ->  RL stays honest (robustness result).
  RHG positive and GROWING          ->  reward hacking EMERGES (the warning result).
Either outcome is the paper's headline. Tear the pod down when the curve is captured.
For the full run: drop --smoke and use --steps 500 (~3-4 h).
EOF
