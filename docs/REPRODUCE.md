# Reproducibility

## Environment
- **EDA:** Icarus Verilog 13.0 + Yosys 0.66 (Homebrew, arm64). OpenLane 2.3.1 (Railway, Sky130A)
  for real PPA. Formal uses `read_verilog -sv`, `async2sync`, `memory`, and a bounded
  `miter + sat -seq 20 -set-init-zero` fallback.
- **LLMs:** via a 9router OpenAI-compatible gateway — `set -a; source ../jerp-docex/.env; set +a`.
  **Pin exact ids** (R20), and **disable gateway auto-fallback during scoring**; log the exact
  upstream id/provider/effort. Ids used: `cc/claude-opus-4-8`, `cc/claude-haiku-4-5-20251001`,
  (`cx/gpt-5.5` available); DeepSeek direct via `RTLG_BASE_URL=https://api.deepseek.com`, id
`deepseek-chat`. LLM calls require the sandbox disabled.
- **Python:** 3.13 (core library is stdlib-only; `openai` only for the agent).

## Deterministic commands
```bash
make demo ; make parsers                       # metric engine + parser checks (no deps)
python3 scripts/run_pilot.py --task tasks/<t> --baselines        # oracle anchors
python3 scripts/import_veval.py --all                            # regenerate VerilogEval tasks
RTLG_MODEL=<id> python3 scripts/run_veval.py --max-iters 2 --out results/<m>.json   # sweep (LLM)
python3 scripts/run_veval.py --candidates-from runs/<m> --out results/<m>_sv.json   # re-score (no LLM)
python3 scripts/report_cis.py ; python3 scripts/analyze_cost.py  # CIs, cost
python3 scripts/gen_ppa_data.py && python3 scripts/train_surrogate.py   # C3 offline
```

## Oracle stages → result files (Opus campaign)
Each hardening stage is a re-score of the SAME 156 candidates (no new LLM); the figures/tables and
`report_cis.py`/`analyze_cost.py` read the **canonical final** stage `resweep5`:
| stage | flags added | result file | honest+bmc | HPR |
|-------|-------------|-------------|-----------:|----:|
| naïve | `equiv_make` only | `results/sweep_opus.json` | 88 | 0.564 |
| +reset+don't-care | `async2sync`, dontcare-reclassify | `results/resweep_opus.json` | 91 | 0.583 |
| +BMC | bounded miter+sat fallback | `results/resweep2_opus.json` | 94 | 0.603 |
| +SV | `read_verilog -sv` | `results/resweep3_opus.json` | 128 | 0.821 |
| +memory | `memory` (case→ROM) | `results/resweep4_opus.json` | 135 | 0.865 |
| **+reset-BMC (canonical)** | `-nolatches` reset-aware Pass-3 | **`results/resweep5_opus.json`** | **140** | **0.897** |

`equiv.py` is the *final* oracle (all flags on); intermediate stages reproduce from the frozen
result files above. The other three models are re-scored on the same final oracle:
`resweep_haiku_p3.json` (113/156), `sweep_deepseek_p3.json` (118/156), `sweep_gpt55_p3.json`
(137/156). (Using `resweep3` instead of `resweep4/5` was the source of the old Opus
HPR 0.82-vs-0.90 mismatch — now every script pins the final stage.)

**GPT-5.5 sweep note.** `cx/gpt-5.5` via the 9router gateway drops calls under a sustained burst when
the gateway's upstream connection blips (both early sweeps failed ~87% with *no candidate written* —
route errors, not model failures). `llm.py` now retries with exponential backoff; the valid sweep has
a real candidate for every task and visible-pass-rate 0.96.

## Determinism notes
- Hidden testbenches use a fixed `$random` seed → a fixed vector set. Yosys formal is
  deterministic; BMC is bounded and seed-free.
- **LLM runs are nondeterministic.** Reported numbers use the pinned ids above with `max_iters=2`.
  For error bars across seeds, run the sweep N times (future); single-run results carry the Wilson
  CIs from `report_cis.py`.
- **Frozen harness:** cite the exact repo commit hash used for a given run in the paper.
- Re-scoring (`--candidates-from`) is fully deterministic (EDA only, no LLM) → oracle changes are
  reproducible against frozen candidates.
