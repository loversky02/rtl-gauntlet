# NEXT — resume checklist (paper must-haves)

**To resume next session:** open Claude in this repo, say *"tiếp tục RTL Gauntlet must-haves"* —
memory auto-loads; then read this file.

**Status (updated):** All must-haves #1–#5 addressed + #6 (negative result). Oracle: false-CEX
9→1, inconclusive 50→6, HPR 87%. **Paper compiled**: `paper/main.tex` → `paper/main.pdf` (6 pp,
`pdflatex`), figures via `scripts/make_figures.py`. C1 ~93% · C2 ~60% · C3 ~45% · Paper ~90%.
Results: `docs/PILOT_RESULTS.md`. Risks: `docs/RISKS.md`. Build PDF: `cd paper && pdflatex main.tex`.

**Remaining (all future-work / polish):** EQY structural-match for the 6 residual FSMs; semantic
(not just identifier) contamination mutation; +1–2 models (gpt-5.5/gemini); author/affiliation;
the ambitious **RLVR training-time hacking** study (separate paper, needs GPU).

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
