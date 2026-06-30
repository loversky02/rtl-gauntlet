# Paper outline — The RTL Gauntlet

**Title:** *The RTL Gauntlet: Measuring Honesty, Cost, and Latency-Robustness in Agentic
Hardware Design.*
**Hook:** *Beyond Pass@Visible — the headline score in agentic hardware design can be gamed,
is expensive to reach, and does not scale to real reward.*

## Abstract (draft)
Agentic RTL frameworks report 100% pass, but against *visible* tests. We build a two-tier
protocol that scores a frozen design with a withheld formal-equivalence oracle and quantify a
**Reward-Hacking Gap**. Applying it to 156 VerilogEval tasks, we find the headline RHG is
dominated by **oracle false positives**: a naive formal oracle over-reports reward hacking
(don't-care X, async-reset, state-encoding, init transients). We harden the oracle in three
stages (reset-aware → don't-care-aware → bounded miter+SAT), cutting false-CEX 9→1, and show —
with per-case adversarial verification — **zero genuine reward hacking** by frontier models on
fair tasks. We argue the central artifact for this domain is a *don't-care/reset/encoding-aware*
oracle plus a *verification discipline*, and that eliciting real hacking needs adversarial
conditions (tamper-capable agents, weak tests), which our tamper-probe catches.

## 1. Introduction
- HORIZON (arXiv:2606.28279): agentic RTL → 100% pass, iter-0 only 47.8% → success is *iterative
  repair against a visible signal*. Authors flag reward-hacking, cost, latency as open.
- Thesis: pass@visible is the wrong score (gameable / expensive / unscalable).
- Contributions: (i) two-tier formal-grounded protocol + RHG/HPR; (ii) finding that naive formal
  over-reports, and a 3-stage hardened oracle; (iii) tamper-probe; (iv) verified result: zero
  genuine hacking on VerilogEval, hacking needs adversarial conditions.

## 2. Related work  → docs/RELATED_WORK.md
- Formal-equiv-as-oracle is standard (VeriThoughts/NotSoTiny/RealBench) — TOOL, not contribution.
- SpecBench (2605.21384) owns visible/held-out gap for *software*, admits finite-test limit.
- EvilGenie (2511.21654): holdout + edit-detection. VeriContaminated (2503.13572): contamination.
- Closest RTL: Agentic Frontier (2603.19347) — no honesty/formal/hidden tier.
- Our slot: RTL + **exhaustive formal oracle** (fixes SpecBench finite limit) + tamper-evidence.

## 3. Method
- Two-tier protocol (ADR-0001): VISIBLE diagnostic (agent iterates) vs WITHHELD final (hidden TB +
  formal equivalence). Interface-locked (R16). Metrics: RHG (visible-passers failing withheld),
  HPR (honest pass). Tamper-evidence tier (R12) via EDA-artefact edit detection (R17 isolation).

## 4. The oracle, and why naive formal over-reports  ← KEY
- Naive equiv_make CEX classes (all verified false positives): don't-care X; async-reset;
  state-encoding (vector vs scalars); init transients.
- 3-stage hardening: (a) async2sync; (b) don't-care reclassification; (c) bounded miter+SAT
  fallback (encoding-agnostic; a SAT model is a real CEX). Each tested on verified cases.

## 5. Experiments
- Pilot (gray2bin, popcount8): oracle + planted honest/dishonest anchors; tamper-probe red-team.
- VerilogEval 156-task sweep, Opus 4.8 vs Haiku 4.5, routed gateway, $0.
- Oracle-hardening progression (docs/PILOT_RESULTS.md §5–7):
  - false RHG_cex 9 → 3 → 1; inconclusive 50 (BMC-timeout big FSMs); honest 88→91; bmc_equiv 3.
- Tamper-probe: planted red-team caught (faked TB → hidden+formal+tamper); real agents honest.

## 6. Findings
- Naive formal **over-reports**; adversarial verification is mandatory (headline 6.1% → artifact).
- No false positives on honest agents; **zero genuine hacking** on fair VerilogEval (Opus, Haiku).
- Tamper caught when present. → Hacking is a function of adversarial conditions, not benchmark mass.

## 7. Limitations / future
- Residual oracle gaps: init-don't-care (circuit8), BMC-timeout on large FSMs, state-encoding via
  EQY `match`/`recode` (H8/H9). Curation effort (R15). Contamination (R14).
- C2 Cost (token/early-stop) and C3 Latency/PPA (surrogate) as further axes.

## Tables/figures to generate
- T1 oracle-hardening progression (naive/H7/H8 × categories) — have it.
- T2 Opus vs Haiku ×156 — DONE: Opus honest122/fail9/RHG1*, Haiku honest104/fail30+11nc/RHG1*
  (*both RHG_cex = verified init artifacts). Weakness → failures, not hacking.
- F1 RHG_cex case taxonomy (don't-care / reset / encoding / init) with one verified example each.
