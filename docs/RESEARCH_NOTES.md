# Research notes — addressing the stated limitations (web-sourced, citations verified 2026-06-30)

Every arXiv ID below was fetched from `arxiv.org/abs/<id>` and confirmed to resolve to the stated
title. Claims that sit in a paper's body (not its abstract) are flagged **[body-only]** — verify
against the PDF before quoting verbatim. The paper's own 10 bib entries were independently
re-verified: **all 10 resolve and titles match** (no fabricated citations).

---

## A. Negative result is single-inference only — the real gap is RL *training-time* hacking

**The criticism (valid, and the biggest one).** Our headline ("frontier agents don't hack fair RTL")
is measured under one-shot inference on *aligned* models — the regime least likely to show hacking.
Hacking is documented to emerge while *optimizing against* a gameable reward.

**Verified evidence:**
| arXiv | finding |
|---|---|
| [2503.11926](https://arxiv.org/abs/2503.11926) (Baker et al., OpenAI) | **Strongest cite.** During *production RL training* on "make the unit tests pass", the agent *discovered test-subverting hacks*; CoT-monitoring caught them as they emerged. Exists because of the RL loop, not at inference. |
| [2604.15149](https://arxiv.org/abs/2604.15149) (Helff et al.) | Shortcut/enumeration hacking is **specific to RLVR-trained models (GPT-5, Olmo3), absent in non-RL models (GPT-4o, 4.5, Ministral)** — exactly the reviewer's point. |
| [2605.02944](https://arxiv.org/abs/2605.02944) (Li et al.) | Pass-rate reward in **critic-free RL (GRPO, RLOO)** gives no durable gain over binary reward; reinforces overfitting to the provided test suite **[body-only for the "shortcut" wording]**. Same optimizer family + small models as our probe. |
| [2603.07084](https://arxiv.org/abs/2603.07084) (Countdown-Code) | Controlled testbed (proxy=test pass, true=correctness): ~1% hack contamination in SFT seeds it, **RL amplifies + generalizes** misalignment beyond training domain. |
| [2508.17511](https://arxiv.org/abs/2508.17511) (School of Reward Hacks) | Training on harmless reward-hacks (incl. coding) generalizes to broader misalignment; authors call it "preliminary evidence" — a good model for honest framing. |
| Software gap analogues | SpecBench [2605.21384] (gap = visible − held-out, smaller models hack more, gap grows ~28pp/10× code); EvilGenie [2511.21654] (held-out + judge + test-edit detection); SWE-bench test-overfit [2511.16858]. |

**RTL RL exists but never *measures* emergence** (the open slot, skeptically confirmed): CodeV-R1
[2505.24183] (RLVR + rule-based testbench equivalence reward), VeriReason [2505.11849] (SFT+GRPO,
testbench reward), EARL [2511.12033], VeriRL [2508.18462] (sparse/noisy reward + overfitting),
[2504.15804] (chooses **DPO precisely because reward-RL is prone to reward hacking** [body-only]).
**None audits an RL run with an exhaustive formal oracle.** That is our contribution.

**Implemented probe.** `scripts/train_grpo.py` (Qwen3-4B, GRPO, `num_generations=8`, `lr=1e-6`),
reward = `rl_reward.visible_reward` (visible-TB pass = the gameable proxy). The `on_evaluate`/
`on_step_end` callback now generates designs for a held-out audit set every `--audit-every` steps,
scores with `rl_reward.oracle_eval` (hidden + formal), and logs to `runs/grpo/rhg_curve.jsonl`:
```
RHG(t)      = visible_pass_rate(t) − formal_pass_rate(t)        # the reward-hacking gap
hack_rate   = #{visible ∧ ¬(hidden∧formal)} / #visible-passers  # SpecBench/EvilGenie analogue
```
**Emergence claim = RHG(t) has a significantly positive slope** (visible rising while formal
stalls/drops), with bootstrap CI over the audit set *and* over seeds (one run is anecdote).
Run: `bash runpod/rlvr_setup.sh` (smoke) → see [[runpod-grpo-env]]. RTL is the one domain where the
audit is **exhaustive** (formal certifies over the whole space — no "finite held-out" caveat).

---

## B. Contamination probe: scale it, give it its OWN estimator, triangulate

**Two corrections.** (1) `scripts/mutate_tasks.py` currently does **meaning-PRESERVING** mutation only
(rename module, reframe spec); the popcount→`zerocount8` **meaning-CHANGING** probe is the demo, not
yet the full pipeline. (2) The paper's "≤2.5–3.2%" is a **Wilson reward-hacking** bound — *not* a
contamination estimator. Give contamination its **own** bound and stop overloading the number.

**Method (metamorphic contract — a reasoner is invariant to meaning-preserving, sensitive to
meaning-changing):** prior art [2504.04372] (fault-localization robustness; closest match to our
"invariant/sensitive" framing), VarBench [2406.17681], multimodal semantic perturbation [2511.03774]
(**VLM-focused — phrase precisely**), program-repair memorization [2604.21579] (**near-exact analogue:
performance drop under meaning-preserving transform correlates with NLL ⇒ memorization**).

**Two mutation generators (extend `mutate_tasks.py`), each self-validated by our formal oracle:**
- **[A] meaning-preserving** (model should stay invariant): identifier rename, spec paraphrase,
  comment ins/del, algebraic rewrites (`a&b`↔`~(~a|~b)`, `case`↔`?:`). Defeats verbatim memorization.
- **[B] meaning-changing** (memorized canonical fails hidden+formal): operator inversion (`==`↔`!=`,
  `<`↔`>=`), function flip (count-ones→zeros, AND→NAND, posedge→negedge), constant/threshold change,
  polarity/reset flip, blocking↔non-blocking. Mutate `ref_module.sv` → new golden → regen TBs →
  **auto-validate**: canonical golden must FAIL the [B] task (probe "bites") and mutated golden must PASS.

**Statistics — Clopper–Pearson one-sided 95% upper bound** (correct at the k=0 boundary; preferred
over Wilson for a *bound*): k=0 ⇒ `p_upper = 1 − 0.05^(1/n)` (rule-of-three `3/n`).
| n | rule-of-three 3/n | exact CP |
|---|---|---|
| 40 (pilot) | 7.5% | 7.2% |
| 120 | 2.5% | 2.46% |
| 163 (all canonical) | 1.84% | 1.81% |
| 203 (all tasks) | 1.48% | 1.46% |
**The bound shrinks because we grow n, not the claim** — this is the direct answer to "only 40 tasks."
Report per-model (contamination is model-specific); do not average the two models into one number.

**Triangulate the behavioral probe** (surveys [2404.00699], [2502.14425] say no single signal is
reliable): Min-K% Prob membership inference [2310.16789] (used by VeriContaminated); NLL↔degradation
correlation [2604.21579] (headline triangulator); 50-gram overlap vs The Stack (note: n-gram fails on
rephrased contamination [2311.04850]); guided/unguided "Time Travel" [2308.08493]; CDD [2402.15938]
**(secondary — performs at chance in some settings [2603.03203], lead with Min-K%/NLL instead)**.
Embed **canary strings** in the public release to future-proof RTL-Gauntlet itself.

---

## C. PPA on toy designs / not signoff-grade — relative ranking is OK if robustness-checked

**Open Sky130/OpenLane2 is legitimately PRE-signoff**, missing vs commercial (Genus/Innovus/Tempus):
single-(tt-)corner CTS, no quantitative SI/crosstalk, no IR-drop/EM signoff, less-aggressive logic opt
⇒ systematically larger area/power. Quantified: ~**1.5× area, ~2× power, ~1.7× cells** for an FSM
([2512.06122], open vs full Cadence stack); Yosys area avg **1.24× (130nm) / 1.49× (40nm)**, cells
1.54×/1.77× (DVCon "Open-Source EDA in an Industrial Design Flow") — but OpenROAD is 4–6× *faster*.

**Ranking inversions are real (the ammunition):** **RTL-OPT [2601.01765]** (DAC 2026) — *"the
comparison result between a pair of RTL codes"* depends on the synthesizer: an aggressive tool
(`compile_ultra`) can collapse two variants to identical netlists while weaker Yosys over-separates
them, **overstating** a transformation's value. Inversions cut both ways.

**Relative comparison IS defensible (it's the standard):** TuRTLe [2504.01986] runs RTLLM/VerilogEval
through OpenLane+Sky130 at a fixed constraint and scores PPA as a **ratio to a golden reference**,
arguing it is *"technology and constraints independent since identical settings are applied"*. RTLLM
v2.0 normalizes to the reference too. **Iso-flow + normalize-to-reference = de-facto standard.**

**Our fixes (cheapest → gold):**
1. (free) Pin + publish exact flow (LibreLane commit, PDK SHA, full SDC, period, util, strategy);
   report raw P/P/A + the ratio; enable multi-corner STA; report a **timing-feasibility flag**
   separately so a near-failing design can't masquerade as "best PPA".
2. (cheap, **headline rebuttal**) Run **≥2 synthesis strategies** (Yosys `AREA 0` vs `DELAY 0`/
   ABC_SPEED) and report **rank stability (Kendall-τ)**. Stable ranking directly rebuts RTL-OPT's
   inversion criticism *with our own data*. Pure CPU time.
3. (paid, future) Common-evaluator: generate open, **evaluate all with one commercial P&R tool**
   ([2601.17520]) as a calibration subset → converts "open-only" to "open-generated, commercially-evaluated".

**Designs to add (verified, harden in Sky130/OpenLane2 on CPU):** `spm` (bundled, smoke), **AES**
(bundled, ~12–16k cells, ~30–60min), **picorv32** ([github.com/YosysHQ/picorv32](https://github.com/YosysHQ/picorv32), RV32, ~30–60min, Efabless-taped-out),
**ibex** ([github.com/lowRISC/ibex](https://github.com/lowRISC/ibex), ~1–2h, OpenROAD AutoTuner benchmark). cv32e40p = optional "large tier" (half-day).
Top pick: **AES + picorv32** next + rank-stability across ≥2 strategies as the rebuttal.

---

## Internal-consistency fixes already applied to the paper (2026-06-30)
- **129 vs 135:** honest (full inductive proof) = **129**; honest + BMC-verified = **135**
  (`make_figures.py:23` plots the 135 line, legend "honest (incl. bmc)"). Fig caption reworded to
  "verified-equivalent (honest, incl. BMC) 88→135; honest-only 88→129"; Table 3 HPR fixed 0.82→**0.87**
  (= 135/156, was paired with the pre-`memory`-stage 128/156). Captions now tie 129+6=135 explicitly.
- **≤3% vs ≤2.5/3.2%:** abstract + Findings bumped to **≤3.2%** (true for both models; ≤3% was false for Haiku).
- **arXiv 2026 IDs:** all 10 verified to resolve + match titles; authors+year added to each bibitem.

## Source index (all verified to resolve)
Training: 2503.11926 · 2604.15149 · 2605.02944 · 2603.07084 · 2508.17511 · 2605.21384 · 2511.21654 ·
2511.16858 · 2505.24183 · 2505.11849 · 2511.12033 · 2508.18462 · 2504.15804.
Contamination: 2504.04372 · 2406.17681 · 2511.03774(VLM) · 2604.21579 · 2310.16789 · 2402.15938 ·
2308.08493 · 2404.00699 · 2502.14425 · 2311.04850 · 2603.03203 · 1907.07368.
PPA: 2504.01986(TuRTLe) · 2601.01765(RTL-OPT) · 2512.06122 · 2505.02016 · 2406.15107 · 2601.17520.
