"""Adapter: VerilogEval spec-to-rtl tasks → RTL Gauntlet task folders.

Each VerilogEval task has _prompt.txt (spec), _ref.sv (golden `RefModule`), and
_test.sv (testbench comparing DUT `TopModule` vs `RefModule`). We map:
  spec.md      ← prompt           (agent sees this)
  golden.v     ← ref, RefModule→TopModule   (for FORMAL equivalence vs candidate)
  ref_module.sv← ref as-is (RefModule)       (for the testbench's golden instance)
  test.sv      ← testbench                    (the VISIBLE grader the agent iterates on)

FORMAL (golden vs candidate, both TopModule) is the withheld exhaustive oracle.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "external/verilog-eval/dataset_spec-to-rtl"

# Start with a few combinational tasks (formal equiv terminates cleanly).
DEFAULT = ["Prob004_vector2", "Prob005_notgate", "Prob007_wire", "Prob006_vectorr"]


def interface_of(golden_src: str) -> str:
    m = re.search(r"(module\s+TopModule\b.*?\);)", golden_src, re.DOTALL)
    return m.group(1) if m else "module TopModule(/* see spec */);"


def sanitize_tb(test: str) -> str:
    """Strip the VCD waveform dump (it forward-references a not-yet-declared wire,
    which iverilog 13 rejects). This touches ONLY the waveform dump — the mismatch
    counting / verdict logic is untouched, so the pass/fail result is identical.
    """
    test = re.sub(r"(?m)^\s*\$dumpfile\([^;]*\);\s*$", "    // $dumpfile removed (iverilog compat)", test)
    test = re.sub(r"(?m)^\s*\$dumpvars\([^;]*\);\s*$", "    // $dumpvars removed (iverilog compat)", test)
    return test


def convert(base: str) -> str:
    prompt = (SRC / f"{base}_prompt.txt").read_text()
    ref = (SRC / f"{base}_ref.sv").read_text()
    test = sanitize_tb((SRC / f"{base}_test.sv").read_text())
    golden = ref.replace("RefModule", "TopModule")

    name = base.lower()
    d = ROOT / f"tasks/veval_{name}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "spec.md").write_text(f"# Spec ({base})\n{prompt}\n")
    (d / "golden.v").write_text(golden)
    (d / "ref_module.sv").write_text(ref)
    (d / "test.sv").write_text(test)
    (d / "task.json").write_text(json.dumps({
        "task_id": f"veval_{name}",
        "top": "TopModule",
        "kind": "veval",
        "source": "verilog-eval",
        "has_reference": True,
        "interface": interface_of(golden),
        "files": {"spec": "spec.md", "golden": "golden.v",
                  "ref_module": "ref_module.sv", "test": "test.sv"},
    }, indent=2))
    return str(d.relative_to(ROOT))


def main() -> int:
    bases = sys.argv[1:] or DEFAULT
    for b in bases:
        print("wrote", convert(b))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
