.PHONY: help env-check demo parsers pilot-baselines pilot setup cvdp sim-image clean

help:
	@echo "RTL Gauntlet targets:"
	@echo "  env-check        verify host toolchain (docker/python/git)"
	@echo "  demo             metric engine on synthetic runs (no deps)"
	@echo "  parsers          verify sim+formal output parsers (no EDA, runs on Mac)"
	@echo "  pilot-baselines  score honest+dishonest anchors (needs iverilog+yosys → RunPod)"
	@echo "  pilot            agentic run via 9router (set RTLG_* env first → RunPod)"
	@echo "  setup            create .venv and install requirements"
	@echo "  cvdp             clone the NVIDIA CVDP harness into external/"
	@echo "  sim-image        build the open-source EDA simulation Docker image"

env-check:
	python3 scripts/check_env.py

demo:
	python3 scripts/demo_metrics.py

parsers:
	python3 scripts/demo_parsers.py

pilot-baselines:
	python3 scripts/run_pilot.py --task tasks/pilot_gray2bin --baselines

pilot:
	python3 scripts/run_pilot.py --task tasks/pilot_gray2bin

setup:
	python3 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -r requirements.txt

cvdp:
	@mkdir -p external
	@test -d external/cvdp_benchmark || git clone https://github.com/NVlabs/cvdp_benchmark.git external/cvdp_benchmark
	@echo "CVDP harness at external/cvdp_benchmark — see its README_AGENTIC.md"

# Apple Silicon: add `--platform linux/amd64` if the arm64 build fails.
sim-image:
	cd external/cvdp_benchmark && docker build -f docker/Dockerfile.sim -t nvidia/cvdp-sim:v1.0.0 .

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
