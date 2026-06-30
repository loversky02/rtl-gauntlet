# Related work & positioning

Prior-art sweep (2026-06-30). Conclusion: **formal-equivalence-as-oracle is already
community-standard and is NOT our contribution.** The open gap — confirmed by search — is
*measuring reward hacking in agentic RTL with a formal oracle*. We reposition around that.

## What is already solved (cite, do not claim)

| Theme | Prior art | What it settles |
|-------|-----------|-----------------|
| Formal equiv allows *multiple correct* implementations | VeriThoughts; [NotSoTiny](https://arxiv.org/abs/2512.20823); [RealBench](https://arxiv.org/abs/2507.16200) (Yosys + JasperGold) | The golden-reference "many valid designs" problem → use formal equivalence, not structural/sim match |
| Golden references contain bugs | [TuRTLe](https://arxiv.org/abs/2504.01986) (6+6 bad samples in RTLLM/VerilogEval) | We must **curate** the golden set, not trust it blindly |
| Token efficiency / cost for agentic RTL | [Token-allocation in agentic HW verif (2604.15657)](https://arxiv.org/abs/2604.15657); PRO-V-R1; VFlow; SymRTLO | The Cost axis (C2) is **crowded** → report it, don't claim novelty |
| Reward-hacking detection via visible/hidden split + monitor | [Countdown-Code (2603.07084)](https://arxiv.org/abs/2603.07084); [Reward-hack detection in code (2601.20103)](https://arxiv.org/abs/2601.20103) | The *methodology* exists — but for **software/math, not RTL, and via LLM monitor, not formal** |
| Reward hacking on the *training* side (RL) | VeriRL (2508.18462); Testbench-Feedback DPO (2504.15804) | They *avoid* reward hacking during RL training; they do not *measure* it at eval time |

## Closest paper (highest scoop risk) — and why it doesn't scoop us

**Exploring the Agentic Frontier of Verilog Code Generation** ([2603.19347](https://arxiv.org/abs/2603.19347))
— "first systematic agentic eval on CVDP" over GPT Codex-5.3 / Claude Opus 4.6 /
Gemini-3.1 Pro / Kimi-K2.5 / GLM-4.7. It does **NOT**: use a hidden-test / two-tier
protocol, use formal equivalence as an oracle, or quantify any reward-hacking / honesty
metric. It reports pass-rate + a failure taxonomy and explicitly defers training-time
adaptation. It leaves the honesty question wide open — exactly our slot.

## The confirmed gap

> No 2026 work unifies **reward-hacking measurement + a formal-equivalence oracle +
> agentic RTL**. Countdown-Code has the measurement (software, LLM monitor); VeriThoughts/
> NotSoTiny/RealBench have the formal oracle (correctness only); Agentic Frontier has the
> agentic RTL eval (no honesty). The intersection is empty.

## Our repositioning

- **Tool, not contribution:** formal equivalence (Yosys/EQY) + hidden randomized TB are the
  *independent oracle*. Their community validation is a feature — it de-risks the harness.
- **Contribution = the measurement + the phenomenon:** define **RHG / HPR**, then show that
  strong agentic RTL systems game the visible signal (edit testbenches, lint, exploit
  evaluator idiosyncrasies — HORIZON's own warning) at a measurable rate, on real models.
- **vs Countdown-Code:** RTL domain + formal/sim oracle instead of a self-referential LLM
  monitor.
- **vs Agentic Frontier:** we measure the *honesty of the pass-rate*, not the pass-rate.
- **One-line framing:** an *honest-evaluation harness for agentic RTL* that HORIZON-style
  systems can adopt to report HPR/RHG instead of pass@visible.

## Closest prior art after the GPT-brainstorm verification (2026-06-30b)

A second sweep (verifying a GPT deep-research brief) surfaced the *real* nearest neighbours —
all confirmed to exist and described accurately:

| Paper | What it does | Relation to us |
|-------|--------------|----------------|
| **SpecBench** ([2605.21384](https://arxiv.org/abs/2605.21384)) | Reward hacking in long-horizon **software** agents: (spec) / (visible validation) / (held-out compose) → gap. spec-complete. | **Closest.** Owns the "visible/held-out gap" idea — for software. Self-admits held-out is *finite, cannot exhaustively certify*. |
| **EvilGenie** ([2511.21654](https://arxiv.org/abs/2511.21654)) | Reward-hack benchmark: holdout + LLM judge + **test-file edit detection** + human review. | Holdout alone "not foolproof"; **edit-detection separates real exploit from mere logic error** → our tamper-evidence tier (R12). |
| **VeriContaminated** ([2503.13572](https://arxiv.org/abs/2503.13572)) | Contamination in Verilog benchmarks; GPT-3.5/4o ≈100% on VerilogEval/RTLLM. | R14 is real → must mutate / use fresh tasks. |
| **Trace2Skill** ([2605.21810](https://arxiv.org/abs/2605.21810)) | Long-context EDA agent; sanitized hidden-verifier feedback on a **private copy**, full telemetry. | R17 isolation blueprint to reuse. |

## Sharpened positioning (the "gap metric" is no longer ours — the oracle is)

SpecBench means we **cannot** claim "first to measure reward-hacking via a visible/held-out gap."
Our defensible novelty narrows to three things SpecBench/EvilGenie do **not** have:

1. **Domain:** agentic **RTL/hardware**, not software.
2. **Exhaustive oracle:** formal equivalence proves identity over the *entire* input/state space —
   fixing the exact "finite held-out cannot certify compliance" limitation SpecBench states. This is
   only possible because RTL has a golden + formal equivalence; software does not.
3. **Tamper-evidence on EDA artefacts:** EvilGenie-style edit detection adapted to testbench /
   assertion / checker / harness tampering — the *intent* signal (R12) on top of the behavioral gap.

One-line: *SpecBench measures reward hacking in software with a finite held-out suite it admits cannot
certify compliance; we bring it to RTL where formal equivalence gives an exhaustive oracle, plus
tamper-evidence from EDA trajectories.*

## Scope decision (post-sweep)

- **C1 Honesty** — primary, deep. Novelty = exhaustive formal oracle + tamper-evidence in RTL (NOT the gap metric per se).
- **C2 Cost** — secondary analysis only; cite 2604.15657 / PRO-V-R1 / VFlow, no novelty claim.
- **C3 Latency/PPA** — future work / one small probe; crowded + unrepresentative signoff.
