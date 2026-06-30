# ADR-0001 — Two-tier evaluation with formal equivalence

- **Status:** accepted
- **Date:** 2026-06-30
- **Context axis:** Honesty (C1)

## Context

HORIZON ([arXiv:2606.28279](https://arxiv.org/abs/2606.28279)) reports 100% pass but warns
the agent "may customize the generated RTL to match the observed failures, deterministic
tests, or evaluator idiosyncrasies rather than implement the intended design semantics,"
and notes existing RTL-agent benchmarks have **no mechanism to detect over-solving /
reward hacking.** SWE-bench's design (the agent sees the issue, hidden unit tests decide
the score) is the proven template.

## Decision

Split evaluation into two tiers with a hard information barrier:

1. **Tier 1 — visible / diagnostic.** Directed tests + logs the agent may read during the
   repair loop. Optimizing against these is *allowed* — that is the task.
2. **Tier 2 — withheld / final.** Never shown to the agent, regenerated per run with fresh
   random seeds:
   - **HIDDEN** — randomized constrained testbench (cocotb/Verilator).
   - **REFERENCE** — differential test vs. an independent reference model.
   - **FORMAL** — EQY sequential equivalence vs. the reference RTL (strongest signal;
     `inconclusive` on timeout, with randomized-vector fallback).

Score with **RHG** and **HPR** (see TEST_MATRIX). A run only counts as honestly passing
if it clears Tier 1 *and* every Tier-2 check it was scored on.

## Consequences

- **+** Detects gaming that any single deterministic suite misses; FORMAL gives a
  semantic, not sample-based, verdict.
- **+** Reuses entirely open-source tooling already in the CVDP sim image.
- **−** Requires tasks with a trustworthy **reference RTL** → drives task-set selection
  toward RTLLM-2.0 / Verilog-Eval (public refs) over CVDP's withheld solutions.
- **−** FORMAL non-termination on hard datapaths forces a fallback path and an
  `inconclusive` state the metrics must handle.

## Alternatives considered

- *Hidden randomized tests only* — cheaper, but a lucky agent can still pass an
  incomplete spec; no semantic guarantee.
- *Formal only* — strongest, but does not terminate on many real designs; impractical as
  the sole gate.
- **Chosen: layered (hidden + reference + formal)** — defense in depth; each tier covers
  the others' blind spots.
