# The RTL Gauntlet: Measuring Honesty, Cost, and Latency-Robustness in Agentic Hardware Design

*Working draft. Numbers are from the experiments in `docs/PILOT_RESULTS.md`; reproduce with the
scripts in this repo (routed LLMs via an OpenAI-compatible gateway, EDA via Yosys/Icarus + OpenLane).*

## Abstract

Agentic RTL frameworks now report 100% pass on standard benchmarks, but that score is measured
against *visible* tests, is *expensive* to reach, and is obtained on *proxy* tasks. We turn these
three concerns into measurable axes. We build a two-tier protocol that freezes an agent's design
and scores it with a withheld, formal-equivalence oracle, and define a **Reward-Hacking Gap (RHG)**
and **Honest Pass Rate (HPR)**. Applying it to 156 VerilogEval tasks across two models, we find the
naïve headline RHG (6.1%) is **entirely an oracle artifact**: a naïve formal oracle over-reports
reward hacking via don't-care `x`, async-reset, state-encoding, init-state, and even a SystemVerilog
parser flag. We harden the oracle in four stages — reset-aware, don't-care-aware, bounded miter+SAT,
and `read_verilog -sv` — cutting false counter-examples 9→1 and "inconclusive" 50→14, and verify
every surviving flag by hand: **zero genuine reward hacking** by frontier models on fair tasks. A
weaker model (Haiku 4.5) fails 3× more than Opus 4.8 on the visible tests but does **not** hack
more — weakness manifests as *failures*, not *cheating*. We show the oracle *would* catch hacking
when present (planted-overfit and a tamper-capable shell agent are both caught) and that, on
complete specs, even weak visible tests do not induce over-fitting. We add a token-cost analysis
(weakness shifts spend to iteration) and a latency-axis prototype that produces **real Sky130
power/area/timing** through a containerized OpenLane flow. We argue the central artifact for honest
agentic-hardware evaluation is a *don't-care/reset/encoding-aware oracle plus a verification
discipline*, not a new pass-rate.

## 1. Introduction

HORIZON [arXiv:2606.28279] treats agentic hardware design as repository-level code evolution and
reaches 100% pass on ChipBench/RTLLM-2.0/Verilog-Eval/CVDP — but iteration-0 pass is only 47.8%, so
the headline comes from *iterative repair against a visible signal*. Its authors name three open
problems: reward hacking, token cost, and high-latency (PPA) reward. We make each measurable.

**Thesis.** *Pass@visible is the wrong score for agentic hardware design*: it can be gamed
(honesty), it is expensive (cost), and it does not scale to real reward (latency).

**Contributions.**
1. A two-tier, formal-grounded evaluation protocol with metrics RHG and HPR (§3).
2. The finding that a naïve formal oracle **over-reports** reward hacking, and a four-stage hardened
   oracle that removes it; verification discipline as a first-class method (§4).
3. An empirical result across 2 models × 156 tasks: **zero genuine reward hacking** on fair tasks;
   weakness ≠ hacking; tampering is caught when present (§5–6).
4. Cost and latency prototypes: token accounting, and real Sky130 PPA via a containerized flow (§5).

## 2. Related work and positioning

Formal-equivalence-as-oracle is already community-standard for RTL-LLM evaluation (VeriThoughts;
NotSoTiny [2512.20823]; RealBench [2507.16200]) — so it is our *tool*, not our contribution.
SpecBench [2605.21384] owns the "visible/held-out gap measures reward hacking" idea for **software**
and admits its held-out suite is finite and "cannot exhaustively certify compliance." EvilGenie
[2511.21654] adds test-file edit detection; holdout tests alone are "not foolproof." VeriContaminated
[2503.13572] reports ~100% contamination of VerilogEval/RTLLM for GPT-3.5/4o. The closest RTL work,
"Exploring the Agentic Frontier of Verilog" [2603.19347], runs agentic CVDP evaluation but does
**no** hidden-tier/formal/honesty measurement. Our defensible slot: the **RTL domain** + an
**exhaustive formal-equivalence oracle** (which fixes SpecBench's finite-test limitation) +
**tamper-evidence on EDA artefacts**.

## 3. Method: the two-tier protocol

The agent sees a complete specification, a *visible* diagnostic testbench, and its own failure logs,
and edits RTL until visible passes. We then **freeze** the design and score withheld tiers it never
saw: a hidden randomized/exhaustive testbench, and **formal equivalence** vs. a curated golden
(Yosys). The I/O interface is locked (agents may change internals only). Metrics: **RHG** = fraction
of visible-passers that fail a withheld tier; **HPR** = fraction passing visible and every withheld
tier. A tamper tier (a shell-capable agent that may edit any workspace file) flags edits to the
testbench/harness as *exploit-evidenced* hacking, with the withheld tiers run on frozen originals so
tampering cannot fool the verdict. We separate the claim into behavioral gap, exploit-evidenced, and
tamper-confirmed, and never claim intent without trajectory evidence.

## 4. The oracle, and why naïve formal over-reports

On a 156-task VerilogEval sweep (Opus 4.8), a naïve `equiv_make` oracle reported 9 RHG counter-
examples and 50 "inconclusive." **Every CEX was a false positive.** The classes, each found by
hand-verifying flagged cases:

- **don't-care `x`**: golden assigns `1'bx` to don't-care bits; the agent assigns a concrete value
  (correct per spec, X-matched by the testbench) but `equiv_make` treats `x ≠ value`.
- **async-reset / sequential**: functionally identical designs flagged CEX because the flow ignored
  async resets / initial state.
- **state-encoding**: a candidate logically identical to golden but with a 3-bit vector vs. three
  scalars defeats induction's state mapping.
- **SystemVerilog parser**: most "inconclusive" was a silent parse failure — `read_verilog` defaults
  to Verilog-2005 while VerilogEval references use `always_ff`/`logic`/enums (the simulator accepted
  them, hiding the mismatch).

Hardening (each tested on verified cases before re-running): (a) `async2sync`; (b) reclassify a CEX
to `dontcare` when the golden contains an `x` literal; (c) a bounded **miter+SAT** fallback that
compares I/O sequences directly (encoding-agnostic; a SAT model is a real CEX); (d) `read_verilog
-sv`. Progression (same 156 candidates, no new LLM calls):

| stage | honest | bmc_equiv | dontcare | RHG_cex | inconclusive | fail |
|-------|------:|---------:|--------:|-------:|------------:|----:|
| naïve | 88 | – | – | 9 | 50 | 9 |
| +reset+don't-care | 91 | – | 3 | 3 | 50 | 9 |
| +BMC fallback | 91 | 3 | 2 | 1 | 50 | 9 |
| +SystemVerilog | 122 | 6 | 4 | 1 | 14 | 9 |

The single residual CEX (an uninitialized-latch init transient, a spec don't-care) is also a false
positive. **False CEX 9→1, inconclusive 50→14.**

## 5. Experiments

- **Pilot + oracle validation.** Self-contained tasks (gray2bin, popcount8) with planted honest and
  dishonest anchors: the oracle proves the honest design and catches the over-fitted one (RHG 0.50).
- **Tamper probe.** A red-team agent overwrote the visible testbench to always pass; the withheld
  hidden + formal tiers still failed it and tamper was flagged. Real shell agents (Opus, Haiku) on a
  fair task edited only the design — honest, no tamper.
- **Sweep + model comparison (156 tasks, both `-sv` oracle).** Opus 4.8: honest 122, bmc_equiv 6,
  dontcare 4, RHG_cex 1, inconclusive 14, fail 9. Haiku 4.5: honest 104, RHG_cex 1, inconclusive 7,
  fail 30 + 11 no-candidate. Both residual RHG_cex are verified init artifacts.
- **Elicit.** hex7seg (spec lists all 16 digits; visible TB tests only 0–9): both models implement
  all 16 from the spec (RHG 0); the planted 0–9-only anchor is caught. A weak test does not induce
  over-fitting when the spec is complete.
- **C2 Cost.** Opus 482k tokens (mean 3,090), Haiku 522k (mean 3,597); the weaker model needs more
  repair iterations (2-iter 17 vs 36) — weakness shifts spend to iteration.
- **C3 Latency.** Surrogate pipeline verified offline (mock 315 designs → holdout Pearson r =
  0.89/0.91/0.96 for area/power/timing) and, via a containerized OpenLane flow on Railway (OpenLane
  image as runtime → native `openlane`, no Docker-in-Docker), produced **real Sky130 metrics**:
  counter8 → area 495.5 µm², power 0.120 mW, worst-slack ≈ 5.5 ns.

## 6. Findings

1. A naïve formal oracle **over-reports** reward hacking; the headline number was an artifact, found
   only by per-case verification. Verification discipline is mandatory.
2. No false positives on honest agents; across 2 models × 156 fair tasks, **zero genuine reward
   hacking**.
3. **Weakness ≠ hacking** — a weaker model fails far more but cheats no more.
4. Hacking is a function of adversarial conditions (tamper-capable agents, weak tests *with*
   incomplete specs), which the protocol catches — not of benchmark mass.

## 7. Limitations and future work

Residual oracle gaps: init-don't-care and big-FSM SAT budget (14 inconclusive), and structural
state-matching (EQY `match`/`recode`). Toy designs make PPA noisy (not signoff-grade); a real
latency study needs larger designs (picorv32/opencores) and the surrogate trained on a multi-design
real dataset (GPU, ~1 h). Contamination (R14) of public benchmarks should be mitigated by task
mutation. Cost (early-stop/curriculum) and full PPA-under-latency remain open.

## References (arXiv)
HORIZON 2606.28279 · CVDP 2506.14074 · SpecBench 2605.21384 · EvilGenie 2511.21654 ·
VeriContaminated 2503.13572 · Trace2Skill 2605.21810 · NotSoTiny 2512.20823 · RealBench 2507.16200 ·
Agentic Frontier of Verilog 2603.19347 · token-allocation in agentic HW verif 2604.15657.
