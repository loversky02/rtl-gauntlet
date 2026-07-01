# NEXT — resume checklist (paper must-haves)

**To resume next session:** open Claude in this repo, say *"tiếp tục RTL Gauntlet must-haves"* —
memory auto-loads; then read this file.

**Status (updated):** All must-haves #1–#5 + #6 (negative) + #7 (4 models) + **oracle residual
CLOSED**. Oracle: false-CEX 9→1, inconclusive 50→**0** (Opus), HPR **90%**. Four models, all verified
RHG=0: Opus **0.90** / GPT-5.5 **0.88** / DeepSeek **0.76** / Haiku **0.72**. **Paper compiled**:
`paper/main.tex` → `paper/main.pdf` (**7 pp**, `pdflatex`), figures via `scripts/make_figures.py`.
C1 ~97% · C2 ~60% · C3 ~45% · Paper ~93%. Results: `docs/PILOT_RESULTS.md`.

**DONE this session:**
- **#3 residual CLOSED** — `-nolatches` reset-aware Pass-3 in `equiv.py` (Pass-3 on inconclusive):
  5 Opus FSMs → bmc_equiv, 1 → dontcare; genuine-diff control still flags a broken candidate. No EQY
  install needed. GPT-5.5 leaves 3 (Conway 256-cell + budget).
- **#7 GPT-5.5 added** (`cx/gpt-5.5` via 9router). Route drops calls under burst when the gateway's
  OpenAI upstream blips → `llm.py` now retries w/ backoff; valid sweep = 0.96 visible-pass, RHG_cex 3
  all verified artifacts (q5b, circuit8 init; prob149 input-space don't-care).

**Remaining (future-work / polish):**
- RLVR training-time hacking study — scaffolded (`scripts/train_grpo.py`, `docs/RLVR.md`), needs GPU.
- Gemini as a 5th model (direct provider = real money → ask first).
- author/affiliation + prettier figures for actual submission.

**Environment (already set up):**
- 9router: `set -a; source ../jerp-docex/.env; set +a` (gives `OPENAI_BASE_URL` + key).
  Models: `RTLG_MODEL=cc/claude-opus-4-8` | `cc/claude-haiku-4-5-20251001` | `cx/gpt-5.5`.
  LLM calls need the sandbox disabled.
- EDA local: `iverilog` + `yosys` via brew (installed). Sweeps: `scripts/run_veval.py`.
- VerilogEval tasks: regenerate with `python3 scripts/import_veval.py --all` (gitignored).

## MUST-HAVE (gate to a submittable v1 — ~1 day)
- [ ] **#1 Contamination + mutation.** Write `scripts/mutate_tasks.py` (rename signals, perturb
  params/encoding, keep semantics); regenerate a mutated subset; re-sweep Opus+Haiku; compare
  RHG/HPR vs. original; add a contamination note. *Saves the "zero hacking" claim from memorization.*
- [ ] **#2 Formal-earns-its-keep.** Plant a candidate that passes a WEAK hidden randomized TB but
  is formally CEX (a corner the finite TB misses). One demo task proving formal > finite tests.
- [ ] **#3 Close 14 inconclusive.** Install `eqy` (oss-cad-suite) + equiv with `match`/`recode` +
  init assumption; re-score. If not crackable → document defensibly. *(Risky/formal-hard.)*
- [ ] **#4 CIs.** Wilson / exact-binomial on RHG (denominator = visible-passers) and HPR; add to
  `metrics.py` + report in results.
- [ ] **#5 Reproducibility.** Pin exact model ids/versions in results, freeze harness commit,
  finalize README run instructions.

## SHOULD-HAVE (de-risk acceptance)
- [ ] **#6 Elicit ≥1 real model RHG>0** in an adversarial condition (weak/incomplete spec or
  shell-tamper). This is the phase-diagram research question — risky, may not converge.
- [ ] **#7 +1–2 models** (gpt-5.5 / gemini via 9router) for generalization vs. Agentic-Frontier trio.
- [ ] **#8 Real shell-agent tamper** (not just the planted red-team).

## FUTURE WORK (state in paper; do NOT block v1)
- **C3 full:** scale OpenLane designs (⚠ `railway.json` MUST be at repo ROOT) → surrogate on real
  data → RunPod GPU ~1 h → agent loop under high-latency reward. Railway project was deleted; redeploy
  fresh. ~2–3 h parallelized for the toy set; larger designs (picorv32) = many more hours.
- **Training-time RLVR hacking** — a separate, more ambitious paper (needs GPU): train a small RTL
  agent with GRPO on a visible-test reward, measure emergence of hacking via hidden+formal.
- Intent measurement (reasoning-trace), surrogate meta-hacking, more task types (debug/verif/reuse).

## Target venue
Methodology + benchmark + finding paper → NeurIPS/ICML **Datasets & Benchmarks**, or **MLCAD/ICCAD**
(EDA tooling). Core story: *naive formal over-reports reward hacking; a hardened oracle + verification
discipline; frontier agents don't hack fair tasks, but the oracle catches it when present.*
