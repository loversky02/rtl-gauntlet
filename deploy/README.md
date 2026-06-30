# C3 deploy — CPU on Railway, GPU on RunPod

**Split:** CPU (OpenLane PPA data-gen) → Railway; GPU (surrogate training) → RunPod.
The Railway worker's base image IS OpenLane 2, so `openlane` runs natively — **no
Docker-in-Docker** (the main setup risk).

## 1. Railway — PPA data-gen (CPU, the long pole)
```bash
railway login
railway init                 # or: railway link <project>
railway up                   # builds deploy/Dockerfile, runs deploy/entrypoint.sh
# attach a Volume mounted at /data for the dataset; then:
railway logs                 # watch the OpenLane flow
# pull the dataset from the volume (dashboard or CLI), drop into results/
```
- **Cost control:** slice the list in `corpus()` (scripts/gen_ppa_data.py) so you run, say,
  20–30 designs first, not 315. Pick a plan with **≥4 GB RAM** (OpenLane P&R is memory-hungry).
- First build pulls a multi-GB image; first run downloads the Sky130 PDK (ciel).

## 2. RunPod — surrogate training (GPU, ~1 h)
```bash
runpodctl create pod --gpuType "NVIDIA RTX A5000" --imageName runpod/pytorch:latest
# copy results/ppa_dataset.jsonl onto the pod, then:
python3 scripts/train_surrogate.py results/ppa_dataset.jsonl   # ridge baseline (swap in a GNN)
runpodctl remove pod <id>    # TEAR DOWN immediately — GPU is metered
```

## Honest caveats (see ../docs/C3_PLAN.md)
- Toy designs (VerilogEval/pilot) → PPA dominated by minimum die + I/O; **noisy, not
  signoff-grade**. Real value needs larger designs (picorv32/opencores).
- Validate on a few designs before the full sweep; combinational designs get `CLOCK_PERIOD:0`.
