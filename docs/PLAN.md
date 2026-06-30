# RTL Gauntlet — Plan

## 1. Thesis

HORIZON ([arXiv:2606.28279](https://arxiv.org/abs/2606.28279)) shows agentic loops reach
**100% pass** on RTL benchmarks — but iteration-0 pass is only 47.8%, so the headline
number comes from *iterative repair against visible signals*. The paper names three open
limitations. They are not three papers; they are three measurement axes of one claim:

> **"Pass@visible" is the wrong score for agentic hardware design.**
> It can be *gamed* (honesty), it is *expensive* (cost), and it does not *scale to real
> reward* (latency).

RTL Gauntlet makes each axis measurable and ships a single study.

## 2. Paper framing

**Title:** *The RTL Gauntlet: Measuring Honesty, Cost, and Latency-Robustness in Agentic
Hardware Design.*

**Abstract hook (thesis, one line):** *Beyond Pass@Visible — the headline score in agentic
hardware design can be gamed, is expensive to reach, and does not scale to real reward.*

- **C1 — Honesty.** A two-tier evaluation protocol that strictly separates *diagnostic
  feedback the agent may see during repair* from *final scoring it never sees*: hidden
  randomized constrained tests, an independent reference model, and formal equivalence
  (EQY). New metrics: **Reward-Hacking Gap (RHG)** and **Honest Pass Rate (HPR)**.
  Hypothesis: agents show RHG ≫ 0 on under-specified ("trap") tasks where visible tests
  are weak.
- **C2 — Cost.** Full token/compute accounting; an **early-stop** policy (halt when the
  marginal probability of a new pass is low) and a **curriculum/triage** scheduler to cut
  the long tail (HORIZON's CID 002 = 56M tokens / 82 iters). Deliverable: a Pareto front
  of Honest-Pass vs. tokens.
- **C3 — Latency.** An agent loop that reasons under slow/sparse/expensive reward by
  querying a trained **PPA surrogate** instead of full synthesis→P&R→timing, with
  asynchronous/batched ground-truth checks. Prototype on OpenROAD + Sky130 for a few
  small designs.

**Positioning (after the 2026-06-30 prior-art sweep — see [RELATED_WORK.md](RELATED_WORK.md)).**
Formal-equivalence-as-oracle is already community-standard (VeriThoughts / NotSoTiny /
RealBench) — so it is the *tool*, not the contribution; its validation de-risks our harness.
The confirmed open gap is **measuring reward hacking in agentic RTL with a formal oracle**:
Countdown-Code has the measurement (software, LLM monitor — not RTL, not formal); the closest
RTL paper, *Agentic Frontier of Verilog* (2603.19347), runs agentic CVDP eval but does **not**
do hidden-tier / formal / honesty at all. Therefore:
- **C1 (Honesty) is primary and deep** — the only empty slot. Contribution = RHG/HPR + the
  empirical phenomenon (strong agents game the visible signal at a measurable rate).
- **C2 (Cost) is secondary** — report it, cite prior art (2604.15657 / PRO-V-R1 / VFlow),
  **claim no novelty**; that axis is crowded.
- **C3 (Latency/PPA) drops to future work / one small probe** — crowded and unrepresentative
  of real signoff; a time sink.

## 3. Architecture

```
                 ┌───────────────────────── Agent (routed LLM) ─────────────────────────┐
   TaskSpec ───▶ │  sees: spec + VISIBLE tests + diagnostic logs  →  edits RTL  →  repeat │
                 └───────────────────────────────┬──────────────────────────────────────┘
                                                 │ final RTL (frozen)
                              ┌──────────────────┴───────────────────┐
                              ▼                                       ▼
                     TIER 1 (visible)                        TIER 2 (withheld, final score)
                     directed tests the                      ├─ HIDDEN  randomized constrained TB (cocotb/Verilator)
                     agent optimized against                 ├─ REFERENCE  differential vs. independent model
                                                             └─ FORMAL  EQY equivalence vs. reference RTL
                              │                                       │
                              └──────────────┬────────────────────────┘
                                             ▼
                          RHG = frac(visible-passers that fail any withheld tier)
                          HPR = frac(tasks passing visible AND all withheld tiers)
```

- **Agent** never sees Tier-2. Tier-2 is regenerated per run (random seeds) so it cannot
  be memorized across iterations.
- **FORMAL** is the strongest tier but may time out on hard datapaths (multipliers); on
  timeout we fall back to high-volume randomized vectors and record `inconclusive`.

## 4. Compute mapping (matches the hourly-GPU / gateway setup)

| Workload | Where | Cost |
|----------|-------|------|
| Agent LLM calls (C1, C2) | OpenAI-compatible gateway (routed) | ~free → run freely |
| EDA (sim, Yosys, EQY) | Docker on Mac (Apple Silicon, arm64) | local, free |
| PPA surrogate training (C3) | rented GPU (H100/A-series), hourly | metered — reserve GPU here, not for inference |
| Ground-truth PPA (C3) | OpenROAD/OpenLane + Sky130, batched async | slow, CPU |

## 5. Roadmap

### Phase 0 — Foundation ✅ (host) / pivoted to RunPod for EDA
- [x] `make env-check` green; CVDP cloned into `external/`; agent contract understood
      (Docker reads `/code/prompt.json`, edits `/code/{rtl,verif,...}`).
- [x] **Decision:** run EDA (Icarus/Yosys) on **RunPod Linux x86**, not arm64 on the Mac
      (kills R6). Host stays Python-only.
- [ ] `bash runpod/setup.sh` on a pod → oracle check passes on real EDA.
- **Exit:** the self-contained pilot scores end-to-end on RunPod.

### Phase 1 — Honesty engine (MVP, first numbers) ⭐
- [x] Two-tier runner built: freeze RTL → HIDDEN TB + FORMAL (Yosys) equivalence
      (`rtl_gauntlet/{sim,equiv,agent,runner}.py`); parsers + metrics verified on the Mac.
- [x] First interface-locked task (`tasks/pilot_gray2bin/`) with honest + planted-dishonest
      anchors (R19) for oracle validation.
- [ ] Run the agentic loop via 9router on the pilot (RunPod) → first real RHG/HPR.
- [ ] Curate ~20–30 tasks **with public reference** (RTLLM-2.0 / Verilog-Eval); add the
      shell-capable CVDP agent (`agent_cvdp/`) to enable tampering/trajectory analysis (R12).
- **Exit:** a table of RHG/HPR per task and per source. *The paper's first figure.*

### Phase 2 — Cost engine
- [ ] Per-iteration token/cost ledger; reproduce a long-tail task.
- [ ] Early-stop policy + curriculum/triage scheduler.
- **Exit:** Honest-Pass-vs-tokens Pareto front; % tokens saved at fixed HPR.

### Phase 3 — Latency extension
- [ ] OpenROAD + Sky130 flow for a few small designs; collect (RTL → PPA) samples.
- [ ] Train PPA surrogate (GPU); plug as a fast proxy reward; async ground-truth checks.
- **Exit:** agent improves a PPA proxy metric under slow reward vs. a synchronous baseline.

### Phase 4 — Writeup (parallel throughout)
- [ ] `paper/` outline (DAC/MLCAD/NeurIPS-D&B style); tables/plots auto-generated from runs.

## 6. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| CVDP withholds reference solutions + 20 datapoints; cats 12–14 need Cadence | Build Tier-2 on **RTLLM-2.0 / Verilog-Eval** (public references); hand-author refs for a small trap set; skip commercial-EDA categories |
| EQY non-termination on hard designs | Size-bound task selection; bounded k-induction; randomized-vector fallback with `inconclusive` status |
| Apple-Silicon Docker/arm64 friction | Prefer arm64 images; fall back to `--platform linux/amd64` emulation or a rented Linux box for sim |
| PPA loop too slow even with surrogate | De-scope C3 to framework + surrogate-only experiment; keep ground-truth as validation slice |
| Can't reproduce HORIZON exactly (code release unknown) | We don't need it — our harness + routed backbone is the system under test; HORIZON is the motivation, not a baseline to match |
| Golden-ref false positives on pipelined/timing variants (formal seq-equiv can't map state) | Exclude pipelined tasks from the FORMAL tier or use combinational equiv where valid; curate the golden set (TuRTLe found 6+6 buggy refs) |
| Novelty thin (formal-equiv eval is community-standard) | **Resolved by repositioning:** formal = oracle, not contribution; novelty = first to *measure reward hacking* in agentic RTL with a formal oracle. Gap confirmed (RELATED_WORK.md) |
| Scooped on Cost axis | C2 is explicitly secondary, cited not claimed; primary novelty is Honesty |

## 7. Open decisions

- **D1 — Base task set for Tier-2.** CVDP-subset (xfer refs) vs. RTLLM-2.0/Verilog-Eval
  (public refs) vs. hybrid. *Leaning: hybrid, public-ref first.*
- **D2 — Agent harness.** Reuse CVDP's Docker agent contract vs. a thin custom loop.
  *Leaning: reuse CVDP contract for portability.*
- **D3 — Which routed model as backbone.** Pick 1 primary + 1 cheaper for ablation.

## 8. References

- HORIZON, [arXiv:2606.28279](https://arxiv.org/abs/2606.28279)
- CVDP, [arXiv:2506.14074](https://arxiv.org/abs/2506.14074) · [code](https://github.com/NVlabs/cvdp_benchmark) · [data](https://huggingface.co/datasets/nvidia/cvdp-benchmark-dataset)
- EQY [docs](https://yosyshq.readthedocs.io/projects/eqy/en/latest/) · SymbiYosys [SBY](https://github.com/YosysHQ/sby)
- SWE-bench (hidden-test inspiration for the two-tier split)
