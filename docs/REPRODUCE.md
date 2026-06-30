# Reproducibility

## Environment
- **EDA:** Icarus Verilog 13.0 + Yosys 0.66 (Homebrew, arm64). OpenLane 2.3.1 (Railway, Sky130A)
  for real PPA. Formal uses `read_verilog -sv`, `async2sync`, `memory`, and a bounded
  `miter + sat -seq 20 -set-init-zero` fallback.
- **LLMs:** via a 9router OpenAI-compatible gateway — `set -a; source ../jerp-docex/.env; set +a`.
  **Pin exact ids** (R20), and **disable gateway auto-fallback during scoring**; log the exact
  upstream id/provider/effort. Ids used: `cc/claude-opus-4-8`, `cc/claude-haiku-4-5-20251001`,
  (`cx/gpt-5.5` available). LLM calls require the sandbox disabled.
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

## Determinism notes
- Hidden testbenches use a fixed `$random` seed → a fixed vector set. Yosys formal is
  deterministic; BMC is bounded and seed-free.
- **LLM runs are nondeterministic.** Reported numbers use the pinned ids above with `max_iters=2`.
  For error bars across seeds, run the sweep N times (future); single-run results carry the Wilson
  CIs from `report_cis.py`.
- **Frozen harness:** cite the exact repo commit hash used for a given run in the paper.
- Re-scoring (`--candidates-from`) is fully deterministic (EDA only, no LLM) → oracle changes are
  reproducible against frozen candidates.
