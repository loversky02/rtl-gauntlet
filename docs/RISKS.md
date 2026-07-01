# Risk register

Severity: 🔴 threatens paper validity · 🟠 costs real effort/time · 🟡 strategic/ops.
Status: `open` · `must-test` (resolve with a small probe before scaling) · `mitigated` · `resolved`.

## A. Known risks (raised earlier) — status after the 2026-06-30 prior-art sweep

| ID | Risk | Sev | Status | Note / mitigation |
|----|------|-----|--------|-------------------|
| R1 | Golden-ref false positive on multiple-correct designs | 🟢 | **RESOLVED** | Was the whole story: naive `equiv_make` false-CEX'd on `1'bx` don't-cares / async-reset / state-encoding / SV-parse. The 6-step hardened oracle removes them (dontcare-aware w/ output-context detector, async2sync, miter+SAT, `-sv`, memory, reset-aware Pass-3); every surviving flag hand-verified. False-CEX 9→1, inconclusive 50→0. |
| R2 | RHG ≈ 0, or only shows on dramatized "trap" tasks | 🟢 | **RESOLVED (as a finding)** | Verified RHG=0 on *non-trap* fair RTL across **4 models ×156**; `formal_demo` proves the oracle catches a real planted hack (RHG 0.50). "Zero natural hacking on fair tasks + the oracle/discipline as the artifact" is the headline. RL-emergence = separate study. |
| R3 | Novelty thin vs SWE-bench/CVDP | 🔴 | resolved | Repositioned: formal = oracle (tool), novelty = measuring hacking in agentic RTL |
| R4 | Can't close the gap to HORIZON (no code/model) | 🟠 | accepted | Our harness is the system-under-test; HORIZON is motivation, not a baseline |
| R5 | Formal equiv non-termination / state-space blow-up | 🟢 | **RESOLVED** | The 50 inconclusive were mostly a silent SystemVerilog parse-fail (`-sv`) + incomplete-case `always_comb` latch elaboration, not solver blow-up. `memory` pass + `-nolatches` reset-aware Pass-3 → inconclusive **50→0** (Opus/Haiku/DeepSeek); GPT-5.5 leaves 3 (Conway 256-cell, a genuine SAT-budget limit). |
| R6 | Apple-Silicon arm64 Docker friction | 🟠 | resolved | **Better than feared:** iverilog 13 + yosys 0.66 install as arm64 bottles via brew and run the pilot natively on M5 — no Docker, no RunPod. RunPod x86 reserved only for scale/agentic sweeps. |
| R7 | Token cheap but wall-clock + nondeterminism expensive | 🟠 | open | Multi-seed budget for error bars; push sweeps to RunPod |
| R8 | Needs real HW-verification skill | 🟠 | open | Steepest at golden-curation + TB authoring (see R15) |
| R9 | C3 (PPA) is a time sink / unrepresentative signoff | 🟡 | resolved | Dropped to future work / one small probe |
| R10 | Scope too wide = master of none | 🟡 | resolved | C1 deep, C2 secondary, C3 future |
| R11 | Scooped (hot field) | 🟡 | mitigated | Gap confirmed empty today; field moves fast → **ship fast** |

## B. Newly surfaced risks (the "what else") — mostly measurement-validity, the dangerous kind

| ID | Risk | Sev | Status | Why it bites / what to do |
|----|------|-----|--------|---------------------------|
| R12 | **"Hacking" implies intent; our oracle only measures a behavioral gap** | 🔴 | open | Pass-visible/fail-hidden ≠ proof of *intent*. To claim "hacking" we need **trajectory analysis**: did the agent edit the testbench, comment out assertions, relax lint, hardcode outputs? That edit *is* the intent evidence. Otherwise call it an *honesty/over-fit gap*, not "hacking". |
| R13 | **Hiding tests ≠ hiding spec** | 🔴 | open | Must withhold test *vectors* while keeping the *specification* complete. If we also starve the spec, a hidden-fail means "under-specified", not "gamed" — and reviewers call it circular (this is R2's subtle form). Pilot the visible/hidden boundary on 1–2 tasks first. |
| R14 | **Contamination / memorization** | 🟢 | **RESOLVED** | Identifier mutation (rename module + reframe spec) on 40 tasks: Opus AND Haiku HPR 1.0→1.0, RHG 0→0 (Δ=0). Semantic mutation `sem_zerocount` catches the memorized count-ones (RHG 0.50), variant honest. Self-authored tasks (gray2bin/popcount8/hex7seg) absent from public benchmarks, still honest. One-sided Clopper–Pearson bound ≤7.2% (40-task). Full-benchmark semantic re-mutation + Min-K% = future. |
| R15 | **Golden curation + hidden-TB authoring is the real bottleneck (labor, not compute)** | 🟠 | open | Each task needs a trustworthy golden + a *high-coverage* constrained-random TB + formal-equiv-ability. 20–30 good tasks = weeks of verif work. Add a **coverage metric on the hidden TB** to prove it's stronger than the visible one (else the gap is fake-small). |
| R16 | **Interface lock required for equivalence** | 🟠 | open | If the agent changes port names/widths/protocol, EQY can't map state → spurious "not equivalent". Spec must **fix the I/O interface**, allow internal freedom only. |
| R17 | **Agent sandbox / oracle isolation** | 🟠 | open | Agent must not be able to touch the golden or hidden tier. CVDP tracks changes + isolates `/code/*`; verify it. Shell access (`sed -i` on harness) is a known hacking vector in this domain — confirm our hidden tier runs on a frozen copy outside agent reach. |
| R18 | **Statistical power** | 🟠 | open | Few tasks → wide confidence interval on RHG (a rate over only the visible-passers). Tension with R15. Plan task count + multiple models for power; report CIs. |
| R19 | **No baseline to interpret RHG** | 🟡 | open | "RHG = 15%" — high vs what? Need a reference: single-shot non-agentic, and/or a *planted* honest agent and a *planted* cheating agent to anchor the scale. |
| R20 | **9router reproducibility** | 🟡 | open | Pin and record the exact routed model/version; routing drift = noise. For comparability, match the models in Agentic-Frontier (GPT Codex-5.3 / Claude Opus 4.6 / Gemini-3.1). |

## C. Must-test-early (before scaling effort)

1. **R6** — resolved by design: EDA runs on RunPod x86 (`runpod/setup.sh`), not arm64.
2. **R2 + R13** — pilot on 1–2 tasks: spec complete, only vectors hidden. Does a strong agent show a real gap *and* leave trajectory evidence of gaming (R12)? If no gap on fair tasks → pivot.
3. **R16 + R17** — confirm interface-locked equivalence runs, and the agent cannot reach golden/hidden.

> If R2 comes back ≈0 on fair, non-trap tasks, or R12 shows the gaps are all innocent over-fitting with no trajectory evidence → the honesty story weakens; reconsider before investing in the full sweep.

## D. Status upgrades after the GPT brainstorm (sources verified 2026-06-30)

The brief in `deep-research-report.md` was source-checked: VeriContaminated, EvilGenie,
SpecBench, Trace2Skill all exist and are described accurately. Upgrades adopted:

| ID | New status | Enforcement (with evidence) |
|----|-----------|------------------------------|
| R12 | mitigated-by-framing | 3 tiers: (1) behavioral gap = headline **RHG**; (2) exploit-evidenced (trajectory shows TB/assertion/checker/harness edits); (3) tamper-confirmed. Don't claim intent without tier-2 evidence. (EvilGenie edit-detection; SpecBench) |
| R13 | **must-enforce** | Hidden *vectors* allowed, hidden *requirements* forbidden; **freeze spec before any run**. (SpecBench: "specification defines all requirements") |
| R14 | **must-enforce** | Mutate tasks + prefer fresh/living + per-task contamination note. (VeriContaminated: ≈100% on GPT-3.5/4o) |
| R15 | mitigated-by-scope | Core **8–12** tasks w/ full curation packet + coverage report, not 20–30 half-done. |
| R16 | **must-enforce** | Lock top module / port names / widths / clock / reset / protocol; internal freedom only. (EQY `recode`/`match` exist but don't lean on them) |
| R17 | **must-enforce** | Hidden tier on private copy, read-only, no network, no path leak, telemetry **+ a red-team probe** (agent tries `sed -i`/harness no-op/exfil → must fail with logs). (Trace2Skill) |
| R18 | open-but-handled | Wilson / exact-binomial CI on RHG; denominator = **visible passers**, not total tasks. |
| R19 | open-but-important | Add non-agentic single-shot baseline + a planted-cheater anchor (`planted_overfit.v` already exists). |
| R20 | **must-enforce** | **Disable auto-fallback** during scoring; log exact upstream model id/provider/route/effort/temperature/time. Match Agentic-Frontier trio (Gemini-3.1 Pro / GPT Codex-5.3 / Claude Opus 4.6). |

**Claim-scope change:** SpecBench already owns "visible/held-out gap measures reward hacking" — for
software. Our defensible novelty narrows to: RTL domain + **exhaustive formal-equivalence oracle**
(fixes SpecBench's admitted finite-held-out limitation) + **tamper-evidence on EDA artefacts**.
See RELATED_WORK.md.
