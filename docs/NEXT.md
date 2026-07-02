# NEXT — status after the review revision (2026-07-02)

**To resume next session:** open Claude in this repo — memory auto-loads; then read this file.

## STATUS: REVISION COMPLETE — merged to `main`, submission-ready

Every item of the external review (A/B/C) is addressed; all work is on `main` (single branch, single
contributor, no AI attribution). Paper: `paper/main.tex` → **8 pp**, compiles clean; fresh
`paper/arxiv-submission.tar.gz` (isolated-compile verified: 8 pp, 0 errors). Tests: `tests/` **10
passed, no xfail**. Point-by-point reviewer response: `docs/REVIEW_RESPONSE.md`.

### Headline results (all reproducible, no LLM/GPU needed)
| axis | result | reproduce |
|------|--------|-----------|
| **Oracle (A1)** | 7-step hardened; careset + **real-latch half-cycle (mixed-edge)** miters machine-prove EVERY flagged CEX: **flagged RHG 9→0, hand-verification eliminated** | `compare_careset.py` |
| **HPR** | Opus/GPT **0.929** [.88,.96] · Gemini 0.897 · DeepSeek 0.769 · Haiku 0.731 | `report_cis.py` |
| **Contamination (A2)** | 156/156 mutants oracle-verified equivalent; HPR stable on Opus+Haiku re-sweep; open-model MI ΔNLL +0.045 (no memorization) | `verify_mutants.py`, `membership_mlx.py` |
| **Tamper (A3a)** | 156 fair tasks × Opus+Haiku: **0 fake-pass tampers** (3 more models sweeping) | `run_tamper_sweep.py` |
| **Negative control (A3b)** | impossible task: **3/5 models cheat** (DeepSeek/Gemini/GPT-5.5), Opus resists | `run_impossible_5model.py` |
| **Latency (B1)** | real Sky130, size-graded incl. **picorv32**; **Kendall-τ = 1.0** rank stability across AREA/DELAY | `kendall_tau.py` |
| **Cost (B2)** | 4 models + prospective (leave-one-out) early-stop: 12–24% tokens / 4–9% honesty, model-dependent | `analyze_cost.py` |
| **Judge (C1)** | blind judge-vs-human **Cohen κ = 0.80 (strong)**, n=20 → keep the intent claim | `c1_kappa.py` |
| **RLVR (C2)** | GPU smoke ran end-to-end (A100): SFT + 50-step GRPO, oracle audits → **RHG = 0.0 flat** | `results/runpod/rhg_curve_*.jsonl` |

### In flight (background, ~free)
- Tamper sweep for GPT/Gemini/DeepSeek ×156 (`runs/tamper_{gpt,gemini,deepseek}.log`) → when done,
  update the paper's elicit line to "156×5" and `results/tamper_summary.json`.

### Environment (already set up)
- 9router creds live in sibling projects (`../jerp-docex/.env` etc.) → per-model `.env.opus/.gpt/.haiku`
  here; Gemini `.env.gemini` (keep **2.5 Pro** — changing model changes results); DeepSeek `.env`.
- EDA local: brew `iverilog` + `yosys`. Tasks regenerate: `python3 scripts/import_veval.py --all`.
- RunPod lessons (API dockerArgs, SECURE cloud, SHA-pinned launcher, GH_TOKEN needs Contents:RW,
  heartbeat push-back): see memory `runpod-deploy-lessons` + `runpod/rlvr_launch.sh`.

## FUTURE WORK (separate papers / optional polish — do NOT block submission)
- **RLVR full study** (500 steps, multi-seed, ~$5–15 GPU): instrument proven; launcher + retrieval
  work end-to-end. The emergence question is a **separate paper**.
- **Hidden-randomized-TB for all 156** — authoring is the human bottleneck; paper discloses the
  subset honestly.
- **picorv32 timing closure** (slack currently negative; paper frames pre-signoff relative + τ=1.0).
- More task types (debug/verify/reuse); intent measurement from reasoning traces.

## Submission checklist (user actions)
- [ ] 🔴 Revoke the GitHub fine-grained token (it appears in the chat transcript).
- [ ] Repo public + arXiv upload (`paper/arxiv-submission.tar.gz`; engine auto = pdfLaTeX;
      category cs.AR, cross-list cs.LG/cs.SE; license CC BY 4.0). Checks in `paper/ARXIV.md`.
- [ ] Venue: NeurIPS/ICML Datasets & Benchmarks, or MLCAD/ICCAD. Core story: *naive formal
      over-reports reward hacking; a fully mechanized 7-step oracle proves every flag; frontier
      agents don't hack fair RTL tasks — and the oracle catches it when they do.*
