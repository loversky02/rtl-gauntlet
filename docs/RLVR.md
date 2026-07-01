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
One command on a GPU pod (A100/H100, x86_64, CUDA 12.x):
```bash
bash runpod/rlvr_setup.sh      # EDA + pinned RL deps + import tasks + 50-step SMOKE (~30-45 min)
```
It runs `scripts/train_grpo.py --smoke`. For the full curve drop `--smoke`:
```bash
python3 scripts/train_grpo.py --model Qwen/Qwen3-4B --glob "tasks/veval_*" --steps 500
```
The reward-hacking gap is appended to `runs/grpo/rhg_curve.jsonl`, one line per audit:
`RHG(t) = visible_pass_rate(t) − formal_pass_rate(t)`. Tear the pod down once captured.
Cost: one GPU for the training run (hours, not the ~$0.3 minutes of the PPA surrogate). This is the
study that justifies the GPU budget — see [[runpod-grpo-env]] for the training-env gotchas.

## Status
Implemented: reward + oracle instrumentation (`rl_reward.py`) reuse the eval stack, and the GRPO loop
(`train_grpo.py`) now has a complete audit callback — every `--audit-every` steps it generates designs
for the held-out set with the current policy, scores them with the withheld hidden+formal oracle, and
logs `{visible_pass_rate, formal_pass_rate, RHG, hack_rate, honest_rate}` to `runs/grpo/rhg_curve.jsonl`.
One-command bring-up: `runpod/rlvr_setup.sh` (deps pinned in `runpod/requirements-rl.txt`).

**Loop validated locally (no GPU).** `scripts/validate_grpo_local.py` runs GRPOTrainer for 2 steps
with a tiny RANDOM Qwen2 model + the cached tokenizer, exercising every path the pod hits
(dataset → reward → generate → `optimizer.step` → oracle audit → `rhg_curve.jsonl`) — clean on CPU in
~12 s. Five integration bugs were fixed and loop-validated this way (after some were, wastefully,
first hit on a rented GPU): `num_generations` must divide the effective batch (→4); `use_vllm=True`
needs a separate `trl vllm-serve` (→False for single-GPU); `rl_reward` used the pilot schema, not
VerilogEval's `test` TB + `RefModule` (fixed); `bf16` only on CUDA; and the 4B `optimizer.step` OOM
(→ `gradient_checkpointing` on GPU). **Deploy discipline: run `validate_grpo_local.py` before any pod.**

**Remaining = the GPU run itself** (not code): Qwen3-4B, single-GPU HF-generate is ~20 h for 500
steps (~\$30, over a small budget); the full study wants a 2-GPU pod with `trl vllm-serve` (~3–5 h).
Self-terminating launcher: `runpod/rlvr_launch.sh` (trap EXIT + 2.5 h net → no runaway cost). This is
a **separate paper**, not part of v1.

## Literature (verified arXiv IDs — see docs/RESEARCH_NOTES.md §A)
- **2503.11926** — production RL training *discovers* test-subverting hacks (invisible to single-shot eval).
- **2604.15149** — reward-hacking shortcuts are RLVR-specific, absent in non-RL counterparts.
- **2605.02944** — pass-rate GRPO/RLOO reward overfits the visible suite, no durable correctness gain.
- **2603.07084** (Countdown-Code), **2508.17511** (School of Reward Hacks) — emergence + generalization under RL.
- RTL RL that optimizes testbench/equiv rewards but never *measures* emergence: 2505.24183 (CodeV-R1),
  2505.11849 (VeriReason), 2511.12033 (EARL), 2508.18462 (VeriRL), 2504.15804 (DPO to dodge reward hacking).
  The open slot: none audits an RL run with an **exhaustive formal oracle** — ours does.
