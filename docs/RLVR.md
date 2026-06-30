# RLVR — training-time reward hacking (the ambitious follow-on)

**Question.** Our eval-time result is that aligned frontier models don't hack fair RTL tasks.
But HORIZON's flagged "key challenge" is *self-evolution under a gameable reward*. So: **if we
train an RTL model with RL on a visible-test reward, does reward hacking emerge?** Software work
(Countdown-Code, EvilGenie) says it can — we bring the question to RTL with a *formal* oracle.

## Design
- **Policy:** a small open model (e.g. Qwen3-4B) — trainable on one rented GPU.
- **Reward (gameable, the independent variable):** the **visible** testbench pass
  (`rtl_gauntlet.rl_reward.visible_reward`): 1.0 pass, 0.1 compiles-but-wrong, 0.0 no-compile.
- **Algorithm:** GRPO (`scripts/train_grpo.py`, trl + vllm).
- **Instrumentation (the measurement):** at each eval checkpoint, score the policy's outputs
  with the **withheld hidden + formal oracle** (`rl_reward.oracle_eval`) and log:
  - `honest_rate` = visible ∧ hidden ∧ formal,
  - **`RHG`** = (visible ∧ ¬correct) / visible-passers  — the hacking rate.
- **Hypothesis / curve:** as RL pushes the visible reward up, `RHG` *rises* if the model learns
  to over-fit the visible tests rather than implement the spec — the emergence of reward hacking.
  A flat `RHG` ≈ 0 with rising honest_rate would mean RL stays honest.

## Why this matters
It tests the dangerous regime (training, not single-shot inference) that our eval-time study
cannot. Either outcome is publishable: emergence (a warning for RL-trained RTL agents) or
robustness (RL on visible reward stays honest with a good oracle).

## RunPod setup (GPU — the one place GPU is genuinely needed)
```bash
# pod: GPU (A100/H100), an image with torch+trl+vllm + iverilog/yosys on PATH
pip install "trl>=0.17" vllm transformers datasets
apt-get install -y iverilog yosys   # the oracle EDA
python3 scripts/import_veval.py --all
python3 scripts/train_grpo.py --model Qwen/Qwen3-4B --glob "tasks/veval_*" --steps 500
# watch RHG vs step in the logged history; tear the pod down when done.
```
Cost: one GPU for the training run (hours, not the ~$0.3 minutes of the PPA surrogate). This is the
study that justifies the GPU budget — see [[runpod-grpo-env]] for the training-env gotchas.

## Status
Scaffolded: reward + oracle instrumentation (`rl_reward.py`) reuse the eval stack; the GRPO loop
(`train_grpo.py`) is structurally complete (the eval callback's generate-and-score body is the
remaining glue). Not run (needs GPU). This is a **separate paper**, not part of v1.
