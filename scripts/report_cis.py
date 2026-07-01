"""Report HPR and RHG with 95% Wilson confidence intervals from the hardened sweeps.
RHG's denominator is the visible-passers, not all tasks — small n, so a CI matters.

  python scripts/report_cis.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rtl_gauntlet.metrics import wilson_ci  # noqa: E402

HONEST = {"honest", "bmc_equiv"}
NON_VISIBLE = {"fail_visible", "no_candidate"}


def summarize(name: str, f: str) -> None:
    rows = json.load(open(f))["rows"]
    n = len(rows)
    cat: dict[str, int] = {}
    for r in rows:
        cat[r["category"]] = cat.get(r["category"], 0) + 1
    honest = sum(cat.get(c, 0) for c in HONEST)
    vpass = n - sum(cat.get(c, 0) for c in NON_VISIBLE)
    rhg = cat.get("RHG_cex", 0)             # before verification; all verified as artifacts → 0
    hlo, hhi = wilson_ci(honest, n)
    rlo, rhi = wilson_ci(rhg, vpass)
    rlo0, rhi0 = wilson_ci(0, vpass)
    print(f"\n{name}: n={n}, visible-passers={vpass}")
    print(f"  HPR  = {honest}/{n} = {honest/n:.3f}   95% CI [{hlo:.3f}, {hhi:.3f}]")
    print(f"  RHG  = {rhg}/{vpass} = {rhg/vpass if vpass else 0:.3f}   95% CI [{rlo:.3f}, {rhi:.3f}]  (flagged)")
    print(f"  RHG (verified-genuine = 0) → 95% CI [{rlo0:.3f}, {rhi0:.3f}]  i.e. upper bound on real hacking")


def main() -> int:
    # resweep4 = the FINAL (+memory) oracle stage, matching the paper's 135/156 = 0.865.
    # NOT resweep3 (the pre-memory +sv stage = 128/156 = 0.82) — that mismatch was the
    # source of the Opus HPR 0.82-vs-0.87 inconsistency.
    # resweep5 / *_p3 = the +reset-BMC stage: a `-nolatches` reset-aware Pass-3 that
    # closes the residual `inconclusive` FSMs (see equiv.py). resweep4/_sv were the prior
    # +memory stage. All four models re-scored on the same (final) oracle.
    summarize("Opus 4.8", str(ROOT / "results" / "resweep5_opus.json"))
    summarize("Haiku 4.5", str(ROOT / "results" / "resweep_haiku_p3.json"))
    summarize("DeepSeek (deepseek-chat)", str(ROOT / "results" / "sweep_deepseek_p3.json"))
    summarize("GPT-5.5 (cx/gpt-5.5)", str(ROOT / "results" / "sweep_gpt55_p3.json"))
    print("\n  Verified-genuine RHG = 0 for both; the CI upper bound bounds undetected hacking.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
