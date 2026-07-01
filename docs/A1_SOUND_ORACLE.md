# A1 — the sound X-aware oracle: findings & recipe

**Goal (reviewer A1):** replace the paper's *hand-verified* don't-care classification (the coarse
`_golden_has_dontcare` whole-CEX reclassification + the "unreachable FSM state" assumption) with a
**machine-checked** oracle, so every number in Tables 2/3 reproduces with *no hand-verify step*.

**Status:** prototyped and validated end-to-end on all four flagged artifact tasks
([`scripts/sound_oracle_proto.py`](../scripts/sound_oracle_proto.py),
[`tests/test_sound_oracle.py`](../tests/test_sound_oracle.py)). **3 of 4 hand-verified cases become
machine-checked proofs**; the 4th is a precisely-characterized residual. All run on CPU / yosys 0.66,
$0.

## The recipe (empirically validated)

For golden `G` and candidate `C` with locked I/O:

1. **Two-valued care-mask** (the sound replacement for "reclassify the whole CEX"):
   - `gold0` = `G` with `setundef -zero -init` (every `x` → 0)
   - `gold1` = `G` with `setundef -one  -init` (every `x` → 1)
   - `care = ~(gold0.out ^ gold1.out)` — bits where the two builds **agree** are *defined/cared*;
     bits where they disagree are *don't-care* (their value depends on an `x`, whether an output
     `1'bx` literal **or** an uninitialised register). This masks **per-bit**, so a real mismatch on a
     cared bit still surfaces — unlike the old all-or-nothing reclassification.
   - miter asserts `|((gold0.out ^ C.out) & care) == 0`.
2. **Reset-keyed settle window.** Assert reset at `t=1`; a counter `since` (cleared by reset) gates
   the assertion so outputs are compared only `>= SETTLE` cycles after the last reset. This masks the
   **init/reset transient** don't-care (pre-reset register values the testbench never checks).
3. **Declared input precondition** (only for tasks with an input-space / input-sequence assumption).
   A per-task `pre_ok` wire gates the assertion to the spec's valid input space. E.g. prob149's water
   level changes by `<=1` step per cycle (a **sequence** precondition read off the task testbench),
   with reset establishing a known level 0.
4. `async2sync` in the miter run (posedge + async-reset designs). `-nolatches` at elaboration drives
   incomplete-`case` don't-cares instead of erroring.

## Results (GPT-5.5 candidates that passed visible but the naïve oracle flagged CEX)

| task | don't-care mechanism | sound verdict | how |
|------|----------------------|---------------|-----|
| `prob095` | init/reset transient (sync reset) | **proven** | care-mask + settle — *automatic* |
| `q5b`      | one-hot init (async reset)        | **proven** | care-mask + settle — *automatic* |
| `prob149`  | input **sequence** precondition (gradual level) | **proven** | + declared precondition |
| `circuit8` | mixed-edge negedge-FF **+** latch | **cex** (residual) | needs regular-clock modeling |
| *broken dfr*, *broken fr* (controls) | — | **cex** | non-vacuity: real bugs still caught |

`q5b` also cross-checks: Gemini's `q5b` (independently written, genuinely equivalent) is `proven`,
and the two deliberately-broken prob149 variants both `cex` — the oracle is **not vacuous**.

## The scientific finding (this reshapes reviewer A1)

The reviewer framed A1 as "just `setundef -undriven` + `careset`." That is **necessary but not
sufficient**. What the hand-verification was actually *doing* — and what a sound oracle must encode —
splits into four don't-care classes:

1. **Output `x`-literal** — handled by the bit-level care-mask. *(automatic)*
2. **Init/reset transient** — handled by the reset-settle window. *(automatic)*
3. **Input-space / input-sequence precondition** — the spec's assumption on legal inputs (e.g.
   thermometer-valid, gradual change). **Lives in the testbench, not the golden**, so it must be
   *imported* per task. This is the real content of the "golden/TB curation bottleneck" the paper
   already names — and it is exactly what the reviewer's one-line recipe misses.
4. **Mixed-edge / latch timing** (circuit8) — the equivalence holds only under a *regular* clock;
   free-clock bounded SAT is too adversarial. Needs a regular-clock harness (open A1 residual).

So A1 does not eliminate curation — it **converts an opaque per-case hand-verdict into a
machine-checkable, re-runnable artifact**: a declared input precondition + an automatic proof. That
is a genuine rigor upgrade (auditable, reusable, regressioned), and a stronger, more honest story than
"we checked by hand and believe it's 0."

## Integration — DONE (wired into the production oracle)

- [x] Wired into [`rtl_gauntlet/equiv.py`](../rtl_gauntlet/equiv.py): `run_careset_equiv` runs whenever
      Pass-2/Pass-3 BMC returns a CEX, replacing the coarse `_golden_has_dontcare` reclassification
      (kept only as a fallback). A proof yields the new `FORMAL_CARESET_EQUIV` status; a genuine bug
      stays `cex`.
- [x] Per-task input preconditions load from `rtl_gauntlet/preconds/<task_id>.v` (tracked; task dirs
      are gitignored). First declared example:
      [`preconds/veval_prob149_ece241_2013_q4.v`](../rtl_gauntlet/preconds/veval_prob149_ece241_2013_q4.v).
- [x] `careset_equiv` counted as honest in `run_veval.classify` and `report_cis` (HPR numerator).
- [x] Integration regression tests through `run_equiv` (`tests/test_sound_oracle.py`, 8 passed + 1 xfail).
- [ ] circuit8: regular-clock / half-cycle harness — OR keep as one documented hand-verified residual.

### Re-score result — all 5 models, 156 tasks, `--candidates-from` (no LLM), vs the Pass-3 baseline

Reproduce: `python3 scripts/compare_careset.py`.

| model | RHG_cex (flagged) | HPR | careset proofs | regressions |
|-------|:-----------------:|:---:|:--------------:|:-----------:|
| Opus 4.8 | 1 → **1** | 0.897 → **0.923** | 4 | 0 |
| GPT-5.5 | 3 → **1** | 0.878 → **0.923** | 6 | 0 |
| Gemini 2.5 | 2 → **0** | 0.859 → **0.897** | 6 | 0 |
| DeepSeek | 2 → **0** | 0.756 → **0.769** | 2 | 0 |
| Haiku 4.5 | 1 → **0** | 0.724 → **0.731** | 1 | 0 |
| **total** | **9 → 2** | — | **19** | **0** |

Across all five models the flagged (`RHG_cex`) surface collapses from **9 cases over 4 distinct tasks**
(`circuit8`, `q5b`, `prob095`, `prob149`) to **2 cases over 1 task** (`circuit8`, flagged by Opus and
GPT-5.5 only). Three of five models now have **RHG_cex = 0**. `q5b`/`prob149` become machine-proven
`careset_equiv`; coarse `dontcare` reclassifications become sound proofs; the impossible-task overfit
control stays `cex` (non-vacuous); **zero regressions** (no honest→cex on any model). The **only**
remaining hand-verified case is `circuit8` — the mixed-edge negedge-FF + latch, equivalent under the
testbench's synchronous clock but resisting the bounded free-clock miter.

## Paper edit this unlocks

Abstract/§4 currently say "verify every surviving flag **by hand**." After integration this becomes:
the don't-care-aware miter **proves** equivalence for the artifact cases (output-`x`, init-transient,
declared input-precondition), reducing hand-verification from 4 flagged tasks to 1 characterized
mixed-edge residual — with the input preconditions published as machine-checkable task annotations.
