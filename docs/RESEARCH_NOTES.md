# Research notes — solving the three stated limitations (web-sourced, 2026-06-30)

## 1. Contamination not thorough (identifier-only → need semantic mutation)
**Finding (ICST 2026 mutation-FL [arXiv:2504.04372]; VarBench [2406.17681]; semantic-perturbation
contamination detection [2511.03774]; "soft contamination" [2602.12413]):** the field's consensus
fix is **semantic-preserving + semantic-changing mutation**, not identifier renaming. Key principle:
*a model that truly reasons is invariant to semantics-preserving changes (rename/paraphrase) and
sensitive to semantics-changing ones (faults); a memorizer collapses.* Contaminated models drop up
to ~46% under semantic perturbation; clean models stay stable. Exact-match decontamination misses
"semantic duplicates" in training corpora — so identifier mutation alone (ours) is necessarily weak.

**Our plan.** Add two mutation classes on top of identifier-rename:
- **Semantic-changing (function mutation):** alter the golden's function in a spec-complete way
  (e.g., `gray2bin`→`bin2gray`, change a modulus/mapping/constant), update spec+TB. A *memorizing*
  model that regurgitates the canonical solution now **fails formal vs. the new golden** — the
  formal oracle directly exposes memorization. This is the strong test.
- **Fault-injection discrimination (ICST 2026):** inject a fault into the golden; a reasoning model
  should *not* reproduce the faulty behavior. Use as a sensitivity check.
Implemented as a demo in `tasks/sem_*` (see `scripts/mutate_semantic.py`).

## 2. Blind spot on complex sequential FSMs (6 inconclusive)
**Finding (EQY `.eqy` config ref; Yosys FSM handling; yosys#626):** the canonical solution is
**EQY with the state registers *excluded as match points* + a sequential SAT strategy** (with
sufficient `depth`) proving the FSM partition holistically; if the re-encoding came from Yosys,
use the **`fsm_recode` mapping file**. **Caution (real pitfall):** merely *blacklisting* state bits
can make genuinely-different machines report "equivalent" — you must *relate* encodings, not just
exclude, and always keep a genuine-diff control that must still CEX.

**Our plan.** Install `eqy` (oss-cad-suite); for the 6 residual FSMs write a `.eqy` with
`[match] no-bit <state>` + a `[strategy seq] use sat; depth N` section; validate against a
genuine-diff control (must CEX). Our bounded miter+SAT already does the I/O-sequence comparison;
the missing piece is enough depth + proper init/reset assumption for the large machines (lemmings).

## 3. PPA noisy on toy designs (not signoff-grade)
**Finding (TuRTLe [2504.01986]; RTL-OPT [2601.01765]; OpenROAD/OpenLANE):** open Sky130/OpenROAD is
**"tapeout-grade pre-signoff evidence, not foundry signoff."** RTL-OPT shows **PPA rankings flip with
the synthesis flow/effort** (only 3–5/12 LLM-optimized RTL beat the suboptimal baseline under
`compile_ultra`), so absolute open-flow PPA is unreliable. Two rigorous fixes:
- **Relative, identical-settings comparison (TuRTLe):** apply the *same* PDK/constraints to all
  designs and compare LLM vs. a **human-optimized reference** — the comparison is valid even if
  absolute numbers are noisy. Frame our PPA as *relative pre-signoff*, not signoff.
- **Larger, realistic designs + commercial flow:** use human-written designer-optimized references
  (RTL-OPT's 36 designs) or cores (IBEX, picorv32, ISCAS) and, for a true signoff claim, Synopsys
  DC + PrimeTime. Toy designs are dominated by minimum-die padding → drop them.

**Our plan.** (a) Re-frame the C3 result as *relative pre-signoff PPA on identical OpenROAD/Sky130
settings* (honest scope, per TuRTLe). (b) Swap toy designs for a few cores (picorv32/IBEX) for a
meaningful sample; note commercial-flow signoff as out-of-scope (budget).

## Sources
ICST26 mutation-FL [2504.04372] · VarBench [2406.17681] · semantic-perturb detect [2511.03774] ·
soft-contamination [2602.12413] · EQY docs (yosyshq) + yosys#626 · TuRTLe [2504.01986] ·
RTL-OPT [2601.01765] · OpenLLM-RTL (ICCAD24) · OpenROAD PPA milestones.
