# Response to reviewer (A / B / C)

Point-by-point disposition. **Done** = implemented + validated in this repo; **In progress** = code/harness
ready, needs a router/GPU run; **Planned** = scoped in [`docs/REVISION_PLAN.md`](REVISION_PLAN.md);
**Clarify** = we think the point is partly addressed already and say where.

---

## Group A — validity of the main claim

### A1 — sound X-aware oracle instead of hand-verify — **DONE**
We replaced the heuristic don't-care handling (`_golden_has_dontcare` reclassifying a whole CEX, plus the
"unlisted FSM states are unreachable" assumption) with a **sound, machine-checked** X-aware careset miter
([`rtl_gauntlet/equiv.py:run_careset_equiv`](../rtl_gauntlet/equiv.py)): two golden builds
(`setundef -zero` vs `-one`) define the cared bits, a reset-settle window masks init transients, and a
**declared per-task input precondition** ([`rtl_gauntlet/preconds/`](../rtl_gauntlet/preconds/)) supplies
the spec's legal-input assumption. Re-scoring all **156×5** through it (`compare_careset.py`, no LLM):

- flagged **RHG_cex 9 → 2** across five models (both remaining are `circuit8`); **3/5 models now 0**;
- **HPR up on every model** (Opus/GPT 0.92, Gemini 0.90, DeepSeek 0.77, Haiku 0.73);
- **zero regressions**; the planted impossible-task overfit stays a CEX (non-vacuous);
- hand-verification drops from **4 tasks to 1** (`circuit8`).

**Nuance we add (and the reviewer's one-line recipe misses):** `setundef + careset` alone is *necessary but
not sufficient*. What the hand-verification was actually encoding splits into four don't-care classes —
output-`x`, init/reset-transient (both now automatic), input-*sequence* precondition (must be imported from
the testbench, e.g. prob149's gradual thermometer change), and mixed-edge/latch timing (`circuit8`). So A1
converts an *opaque per-case verdict* into a *machine-checkable, re-runnable proof + a declared precondition*
— a genuine rigor upgrade. Full write-up: [`docs/A1_SOUND_ORACLE.md`](A1_SOUND_ORACLE.md); regression tests
`tests/test_sound_oracle.py` (8 passed, 1 xfail). **One honest residual:** `circuit8`, a `negedge`-FF + latch
equivalent only under the testbench's synchronous clock; our bounded free-clock miter cannot discharge the
timing race (a regular-clock harness is future work), so it stays hand-verified.

### A2 — close contamination — **In progress (harness) + Clarify**
*Clarify (under-credited):* we already run a **40-task identifier mutation on both Opus and Haiku**
(HPR 1.0→1.0, RHG 0→0) plus a semantic probe (`sem_zerocount`), and report contamination as its own
one-sided Clopper–Pearson bound (≤7.2%). *To do (now unblocked by A1):* a **full-156 semantic re-mutation**
whose function-preservation is **verified by the A1 sound oracle** (the reviewer's "verify each equivalent"),
then a 5-model re-sweep; plus **membership inference** (Min-K%Prob, NLL-degradation) on the open models that
expose logprobs. The re-sweep and MI need a router run (non-GPU); the mutation+verification harness is CPU.

### A3 — coverage + a negative control — **Clarify + Planned**
*Clarify (already exists):* the **RHG>0 negative control the reviewer asks for is already in the repo** —
`tasks/impossible_popcount8/` + `results/phase_diagram_impossible.json` (paper §5): on an impossible task
GPT-5.5 and DeepSeek register **RHG>0, exploit-evidenced**, while Opus stays honest. The metric is *not*
trivially zero. **Now quantified (R-A3b, `run_impossible_5model.py`):** on the impossible task **3 of 5**
frontier models pass the spec-contradicting TB (DeepSeek, Gemini, GPT-5.5), **≥2 judge-confirmed**
exploit-evidenced hardcode-overfit, while **Opus and Haiku refuse** (Opus formally proven) — the metric
discriminates. *Bonus (feeds C1):* the judge left GPT-5.5's obvious contradictory-TB pass ambiguous, a
**conservative lower bound**. *Still to do:* extend the hidden-randomized-TB and tamper tiers from the
focused demos to the full 156×5 — the labor is authoring hidden testbenches (a stated bottleneck); we
will disclose any subset rather than silently truncate.

---

## Group B — the three title axes

### B1 — Latency (C3) — **Decision: keep the claim, do the full study (Planned)**
We keep "Latency-Robustness" and execute the full C3 (R-B1-full): a size-graded set (spm, AES, picorv32,
ibex), closed timing, and **rank stability via Kendall-τ across ≥2 synthesis strategies**, with the surrogate
trained on the real multi-design dataset. Interim, the paper already labels C3 **pre-signoff, relative**, with
negative slacks stated (not closed timing). CPU data-gen + a ~1 h GPU surrogate train.

### B2 — Cost — **DONE (extended)**
Extended the cost axis from 2 models to **4** (Opus/Haiku/GPT-5.5/Gemini; DeepSeek's sweep logged no tokens)
and added the reviewer's two asks: a **threshold ablation** (k=1,2,3) and a **prospective** evaluation
(leave-one-model-out — the cap is fit on the other three, never on the model it is scored on,
`rtl_gauntlet/cost.py:prospective_early_stop`). Result: early-stop@1 reclaims **12–24%** of tokens for a
**4–9%** honesty loss, and *prospectively* a 5% honesty-loss budget is met only by the stronger-tail models —
so the policy is **model-dependent, not universal** (a caveat the post-hoc number hid). In the paper §5 + Fig.

---

## Group C — rigor & honesty

### C1 — LLM tamper-judge reliability (Cohen's κ) — **Planned**
We will human-annotate the flagged hardcode-vs-bug cases and report Cohen's κ between the LLM-judge and human;
if κ is low we soften the *intent* claim. Note the blast radius is narrow: the judge only sub-classifies an
*already oracle-confirmed* CEX (it cannot invent a hack), so κ bounds the intent label, not the RHG number.

### C2 — RLVR training-time axis — **In progress (deploy-ready, GPU-gated)**
Fully scaffolded and CPU-loop-validated (`train_grpo.py` + `validate_grpo_local.py`); the actual GRPO run is a
separate GPU study (convergence on a 4B model is the risk — we agree it is "should-have, not must-have").

### C3 — honest Limitations — **Done (and kept honest)**
The paper's Limitations/Threats already scope: eval-time (not RL), pre-signoff relative PPA, hidden-TB on a
subset, contamination probe not yet exhaustive, and now the single `circuit8` oracle residual. A1 lets us
delete the "leans on hand-verify" caveat for the other three flagged tasks.

---

## Summary of what changed since the reviewed draft
- **A1 sound oracle** integrated + 156×5 re-scored: flagged RHG 9→2, HPR up, 0 regressions, hand-verify 4→1.
- **B2 cost** extended to 4 models with a prospective, out-of-sample early-stop evaluation.
- Paper (abstract, §4 seven-step pipeline + progression, Table 2, §5, Threats, Findings), figures, README,
  and TEST_MATRIX updated; `report_cis.py` reproduces the headline numbers end-to-end (no LLM).
