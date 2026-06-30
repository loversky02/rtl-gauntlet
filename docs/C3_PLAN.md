# C3 — Latency axis (PPA surrogate): compute & time estimate

**The only phase that needs a GPU.** Everything else (oracle, sweeps, elicit, C2 cost) is
LLM-via-9router (~free, I/O-bound) + CPU EDA — renting a GPU for those wastes money.

## Breakdown

| step | hardware | wall-clock | rough cost |
|------|----------|-----------|-----------|
| 1. Data-gen — OpenROAD/OpenLane synth→P&R→STA on Sky130, per RTL design | **CPU** (multi-core) | ~2–15 min/design; **~3–12 h** for 1–5k designs (parallel on 16–32 cores) | CPU pod $0.05–0.3/h → **~$1–4** |
| 2. Train PPA surrogate (GNN/MLP: RTL/netlist features → power/area/timing) | **GPU** | **~10–60 min** (small surrogate) | A4000/A5000 $0.15–0.4/h → **~$0.2–0.4** |
| 3. Agent loop on surrogate reward + async ground-truth recheck | CPU + routed LLM | seconds/query (surrogate); ground-truth batched async | ~$0 (9router) |

## Answers to "how long on RunPod GPU?"

- **GPU time is only step 2 ≈ 1 hour**, on a *cheap* card (A4000/A5000). An **A5000 hour ≈ $0.3**.
  H100/B300 is overkill for a small surrogate — keep those for real LLM weight-updates.
- **The long pole is step 1 (data-gen), and it is CPU, not GPU** — hours of OpenROAD runs.
  Run it on a cheap CPU pod or the Mac; spin the GPU up *only* for the ~1 h of training, then
  tear it down so the GPU isn't idling on $/hour.
- **First end-to-end C3 ≈ half a day wall-clock, ≈ $2–8 total** (mostly CPU data-gen, ~$0.3 GPU).
- Iterating the surrogate (retrain on more data) is then ~minutes of GPU each.

## What does NOT need a GPU (do on Mac / cheap CPU, ~$0)
- The whole honesty oracle + 156-task VerilogEval sweeps (done — ~20–40 min each on M5).
- H10 oracle polish (yosys/SAT — CPU).
- Elicit experiments + C2 cost (LLM via 9router + CPU EDA).

→ Recommendation: only rent a GPU when you actually reach step 2. Until then, $0.
