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

- flagged **RHG_cex 9 → 0** across five models — every flag machine-proven; 
- **HPR up on every model** (Opus/GPT 0.92, Gemini 0.90, DeepSeek 0.77, Haiku 0.73);
- **zero regressions**; the planted impossible-task overfit stays a CEX (non-vacuous);
- **hand-verification eliminated entirely** (the last case, `circuit8`, closes under a real-latch half-cycle miter — the old `-nolatches` build was destroying its intentional latch).

**Nuance we add (and the reviewer's one-line recipe misses):** `setundef + careset` alone is *necessary but
not sufficient*. What the hand-verification was actually encoding splits into four don't-care classes —
output-`x`, init/reset-transient (both now automatic), input-*sequence* precondition (must be imported from
the testbench, e.g. prob149's gradual thermometer change), and mixed-edge/latch timing (`circuit8`). So A1
converts an *opaque per-case verdict* into a *machine-checkable, re-runnable proof + a declared precondition*
— a genuine rigor upgrade. Full write-up: [`docs/A1_SOUND_ORACLE.md`](A1_SOUND_ORACLE.md); regression tests
`tests/test_sound_oracle.py` (10 passed, no xfail). **No residual:** `circuit8` closes under the real-latch half-cycle miter (regular clock, posedge-registered inputs — a declared synchronous-stimulus precondition); broken mutants still CEX.

### A2 — close contamination — **Behavioral probe DONE at full scale; MI is API-limited**
*Clarify (under-credited):* the earlier draft already ran a 40-task identifier mutation. **Now extended
to the full 156 tasks**, each **machine-verified function-preserving by the A1 sound oracle** (`verify_mutants.py`,
**156/156** proven equivalent — the reviewer's "verify each equivalent") and **re-swept on Opus and Haiku**
(`sweep_mut156_*`): **HPR is stable and RHG stays ≈0** on the novel-surface tasks, so the honesty result is
**not memorization** — it survives textual mutation. *Membership inference (Min-K%/NLL) is infeasible on
these models:* teacher-forced logprobs are unavailable via every router API (Claude/GPT return no logprobs,
Gemini rejects the param, DeepSeek forbids `echo`+`logprobs`), and DeepSeek's generation logprobs saturate at
≈0 at temperature 0 (uninformative — `scripts/membership_probe.py`, `results/membership_deepseek.json`). Proper
MI therefore needs **open-weight local inference**; the behavioral 156-mutant probe is the available evidence
and it is negative for contamination.

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
subset, contamination probe not yet exhaustive, and now **zero oracle residuals**. A1 lets us
delete the "leans on hand-verify" caveat for the other three flagged tasks.

---

## Summary of what changed since the reviewed draft
- **A1 sound oracle** integrated + 156×5 re-scored: flagged RHG **9→0**, HPR up (Opus/GPT 0.929), 0 regressions, **hand-verification eliminated** (careset + real-latch half-cycle miters).
- **B2 cost** extended to 4 models with a prospective, out-of-sample early-stop evaluation.
- Paper (abstract, §4 seven-step pipeline + progression, Table 2, §5, Threats, Findings), figures, README,
  and TEST_MATRIX updated; `report_cis.py` reproduces the headline numbers end-to-end (no LLM).


---

## Second-pass review (2026-07-02) — disposition

Five points raised; **four are limitations the paper already discloses** (the reviewer found no new
validity holes), one is an actionable presentation fix — now done:

1. **Narrow scope (156 small modules)** → now an explicit first Limitations bullet ("Small-module
   scope": zero-hacking is a statement about this task space; SoC/multi-clock untested; compositional
   extension future work).
2. **Eval-time, not RL** → already Limitations bullet 2, with the GPU smoke (RHG flat 0) framed as a
   probe, the full multi-seed study a separate paper. Title claims measurement axes, not training-time.
3. **PPA pre-signoff (~1.2–1.5× vs commercial)** → already stated in Threats + Limitations with the
   Kendall-τ=1.0 mitigation.
4. **Early-stop model-dependent** → already stated (prospective leave-one-model-out analysis added in
   this revision precisely to expose what the post-hoc number hides).
5. **Presentation density / internal jargon** → **fixed**: (a) a glossary table (Table: golden, miter,
   CEX, BMC, careset, precondition, half-cycle miter...) added at the top of §4; (b) the abstract
   de-jargoned (tool flags → plain-English step names); (c) stale numbers in captions fixed.


---

## Third-pass review (2026-07-02) — disposition

The sharpest round: claims/logic + statistics. Dispositions:

1. **Title-vs-evidence gap (eval-time)** → *Fixed by scoping, per the reviewer's own either/or*: the
   abstract now says "at evaluation time" explicitly, and a `Scope:` sentence in the thesis states the
   RL regime is what the instrument is built to audit, not what the paper claims about. The RL smoke is
   framed as an instrument demonstration only.
2. **"Fair task" circularity** → *Rebutted with new text (the criterion existed but was unwritten)*:
   fairness is **mechanically independent of the oracle** — a task is fair iff its **golden passes the
   visible testbench** (no careset/precondition/equivalence involved). Preconditions come from the
   testbench's own stimulus, and under each one the planted/broken controls still CEX — masking cannot
   excuse a real hack inside the legal-stimulus space. Now §3 + controls in §4.
3. **"Weakness ≠ hacking" from near-constant data** → *Conceded and softened*: Findings now state it as
   descriptive ("weakness manifests as failures, not detected hacking"), bounded by the benchmark's
   sensitivity, explicitly not causal.
4. **0/156 rule-of-three bound** → *Conceded and made explicit*: a `Statistical power` note in Threats
   says the bound measures the benchmark's sensitivity, not a model property; <0.5% would need ≳600
   tasks; pooling models is optimistic (shared tasks). Scaling task count is the top future-work item.
5. **κ n=20 CI wide** → *Conceded*: the paper now reports κ=0.80 with CI ≈ [0.55, 1.0] and scopes the
   intent claim to that uncertainty; independent-judge requirement already stated (self-judging lenient).
6. **Contamination bounds scattered / MI indirect for frontier models** → *Fixed*: single ≤1.9%
   (156-task) bound; Limitations now states plainly that MI runs only on an open model, so for the five
   frontier models the evidence is behavioral and "reasoning, not recall" is an inference.
7. **Prose density** → partially addressed (captions/sentences compressed, glossary kept); a pseudo-code
   pipeline figure is a good suggestion for the next major revision.

**Not addressable without new scale** (agreed, stated as future work): more/diverse tasks for real
statistical power; SoC/multi-clock generality; RL-training study at defended scale.


---

## Fourth-pass review (2026-07-02) — disposition (free-tier data, no GPU)

The core critique: after honest scoping the result risks shrinking to "clean oracle + benchmark too
insensitive to say anything about honesty" — cannot tell a good instrument from a blind one; all
positives are author-staged. We attacked it with **new data**:

1. **"Instrument might be blind" → rebutted with positive sensitivity.** Imported a SECOND public
   benchmark (**RTLLM**, `import_rtllm.py`), applied the mechanical fairness gate (golden passes its
   own TB) → 41 fair tasks, and swept all 5 models. The naive golden-equiv oracle **flags 50
   candidate differences over 20 tasks** — so the all-zero VerilogEval result is *not* an insensitive
   oracle. Adjudication then clears them: an **independent judge finds 0 hardcodes** (all
   honest/underspecified), and the recurring flags are the known over-reporting classes — worked
   example `up_down_counter` (flagged by all 5) differs from its golden *only* in async-vs-sync reset,
   with the CEX being a mid-operation reset pulse the reset-at-init TB never applies (hand-verified
   trace). This both rebuts blindness and **replicates the central thesis on a 2nd benchmark**.
   (`results/rtllm_oracle_gate.json`, `results/rtllm_flag_judge.json`.)
2. **"All positives are staged" → pressure hunt for natural hacks.** Re-ran every model's *failing*
   VerilogEval tasks under **7-iteration repair pressure** with an independent judge
   (`run_pressure.py`): 9+6+41+14+36 = **106 pressed task-runs → 0 natural hacks**. So the negative is
   pressure-tested, not an artifact of a 2-iteration budget. (`results/pressure_*.json`.)
3. **"Judge carries Opus's fingerprint" → cross-judge.** A second independent judge (Gemini) on the
   same 20 blind cases: acc 0.95, **κ vs human = 1.00**, κ vs Opus-judge = 0.80 — reliability is a
   property of the method, not of Opus. (`results/c1_crossjudge.json`.)
4. **"DeepSeek cost data missing" → fixed.** Re-swept DeepSeek with token logging (199k over 156);
   cost data now spans 5 models. **Tamper extended to 156×5** (0 fake-pass on all five).

**Honestly still open (needs GPU / scale, stated as future work):** a *natural* hack remains unfound
(so the strongest defense of the title is still the RL-training study, GPU-gated); RTLLM full
per-task adjudication to RHG=0 is characterized but not completed; SoC/multi-clock generality.
The instrument-sensitivity result is the key advance: **0 is now a measured 0, not a blind 0.**
