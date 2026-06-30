"""Phase-0 environment check. Host needs Docker + Python + git; the EDA tools
(Yosys/Verilator/Icarus/cocotb/EQY) live INSIDE the CVDP sim image, so they are
optional on the host.

Run: python3 scripts/check_env.py   (or `make env-check`).
"""

from __future__ import annotations

import shutil
import subprocess
import sys

# (name, version-cmd, required-on-host?)
CHECKS = [
    ("docker", ["docker", "--version"], True),
    ("git", ["git", "--version"], True),
    ("python3", [sys.executable, "--version"], True),
    ("make", ["make", "--version"], False),
    # Optional on host — normally provided by the Docker sim image:
    ("yosys", ["yosys", "--version"], False),
    ("verilator", ["verilator", "--version"], False),
    ("iverilog", ["iverilog", "-V"], False),
    ("eqy", ["eqy", "--version"], False),
]


def _probe(cmd: list[str]) -> str | None:
    if shutil.which(cmd[0]) is None:
        return None
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        line = (out.stdout or out.stderr).strip().splitlines()
        return line[0] if line else "(present)"
    except Exception as e:  # noqa: BLE001
        return f"(error: {e})"


def main() -> int:
    print("RTL Gauntlet — environment check\n")
    missing_required = []
    for name, cmd, required in CHECKS:
        ver = _probe(cmd)
        tag = "REQ" if required else "opt"
        if ver is None:
            mark = "✗" if required else "·"
            print(f"  {mark} [{tag}] {name:10s} not found"
                  + ("" if required else "  (expected inside Docker sim image)"))
            if required:
                missing_required.append(name)
        else:
            print(f"  ✓ [{tag}] {name:10s} {ver}")

    print()
    if missing_required:
        print(f"  ✗ missing required host tools: {', '.join(missing_required)}")
        return 1
    print("  ✓ host ready for the Docker EDA path. Next: `make cvdp && make sim-image`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
