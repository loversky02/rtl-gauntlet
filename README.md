# RTL Gauntlet

**Measuring Honesty, Cost, and Latency-Robustness in Agentic Hardware Design.**

Agentic RTL frameworks now report *100% pass* on RTL benchmarks (e.g. HORIZON,
[arXiv:2606.28279](https://arxiv.org/abs/2606.28279)). But that number is measured
against *visible* tests, it is *expensive* to reach, and it is obtained on *proxy*
benchmarks. HORIZON's own authors flag three open problems. RTL Gauntlet turns those
three problems into three measurable axes and one coherent study:

| Axis | Question HORIZON leaves open | What we measure |
|------|------------------------------|-----------------|
| **Honesty** | Is the 100% real, or did the agent fit the visible tests / evaluator quirks? | **Reward-Hacking Gap (RHG)** + **Honest Pass Rate (HPR)** via a two-tier protocol (diagnostic-visible vs. hidden randomized tests + independent reference + formal equivalence) |
| **Cost** | 100% is easy; *cheap* 100% is not — one category burned 56M tokens / 82 iterations | Pareto curve of Honest-Pass vs. tokens, with **early-stop** and **curriculum/triage** to cut the long tail |
| **Latency** | Real PPA reward (synthesis → P&R → timing) takes hours–days, not seconds | An agent loop that reasons under **slow, sparse, expensive** reward via a trained PPA **surrogate** + async evaluation |

> Honesty and Cost are the cheap, fast, demo-able core (LLM calls routed through a
> gateway, EDA tools run inside Docker). Latency is the ambitious extension.

## Why it's feasible

Almost the entire substrate is already open-source:

- **Tasks + agentic harness:** NVIDIA [CVDP](https://github.com/NVlabs/cvdp_benchmark)
  (783 problems, 13 categories, Docker custom-agent support) +
  [RTLLM-2.0 / Verilog-Eval](https://github.com/NVlabs/cvdp_benchmark) for tasks with
  public reference designs.
- **Hidden-tier scoring:** [YosysHQ/eqy](https://github.com/YosysHQ/eqy) (formal
  sequential equivalence) + cocotb/Verilator randomized testbenches — all bundled in the
  CVDP sim image (Yosys 0.40, Verilator 5.038, Icarus, cocotb 2.0.1).
- **Agent backbone:** routed through an OpenAI-compatible gateway; no local GPU needed
  for Honesty/Cost. GPU is reserved for training the PPA surrogate (Latency axis).

## Status

🟢 **Phase 0 done · Phase 1 in progress.** Self-contained two-tier pilot built and verified
on the Mac (parsers + metric engine); EDA (Icarus/Yosys) runs on **RunPod x86** via
`runpod/setup.sh` (sidesteps arm64). Next: agentic run via 9router for the first real
RHG/HPR. See [docs/PLAN.md](docs/PLAN.md), [docs/RISKS.md](docs/RISKS.md),
[docs/RELATED_WORK.md](docs/RELATED_WORK.md), [docs/TEST_MATRIX.md](docs/TEST_MATRIX.md).

## Quickstart

```bash
make env-check     # verify docker / python / git toolchain
make demo          # run the metrics engine on synthetic runs (no deps, proves it works)
make cvdp          # clone the NVIDIA CVDP harness into external/
make sim-image     # build the open-source EDA simulation image (Docker)
```

## Layout

```
rtl_gauntlet/      core library (task schema, two-tier metrics) — stdlib only
docs/              PLAN, TEST_MATRIX, decisions/ (ADRs)
scripts/           env check, demos, runners
tasks/             curated task sets (reference RTL + visible/hidden tests)
external/          third-party harnesses (CVDP), gitignored
```

## References

- HORIZON — *Agentic Hardware Design as Repository-Level Code Evolution*, [arXiv:2606.28279](https://arxiv.org/abs/2606.28279)
- CVDP — *Comprehensive Verilog Design Problems*, [arXiv:2506.14074](https://arxiv.org/abs/2506.14074) · [code](https://github.com/NVlabs/cvdp_benchmark) · [data](https://huggingface.co/datasets/nvidia/cvdp-benchmark-dataset)
- EQY — equivalence checking with Yosys, [YosysHQ/eqy](https://github.com/YosysHQ/eqy)
