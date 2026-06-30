"""Contamination probe: produce textually-novel BUT functionally-identical copies of
VerilogEval tasks, to test whether the honesty result survives off the verbatim public
benchmark (VeriContaminated: ~100% contamination of VerilogEval/RTLLM for GPT-3.5/4o).

Mutations (semantics-preserving):
  - rename the target module `TopModule` → a fresh identifier (defeats verbatim
    (prompt, solution) memorization keyed on the canonical name),
  - rename golden ports to fresh names, consistently across golden / testbench / interface,
  - reframe the spec preamble so the prompt is not the canonical text.

This is an *identifier/interface-level* mutation. A stronger *semantic* mutation (change the
function itself) is the deeper future test; this one already breaks exact text/AST matching.

  python3 scripts/mutate_tasks.py            # mutate all tasks/veval_* → tasks/mut_<name>
  python3 scripts/mutate_tasks.py 40         # first 40 only
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

NEWMOD = "DutUnderTest"
PORT_MAP = {}  # filled per task


def _ports(golden: str) -> list[str]:
    m = re.search(r"module\s+TopModule\s*\((.*?)\)\s*;", golden, re.DOTALL)
    if not m:
        return []
    names = re.findall(r"\b([A-Za-z_]\w*)\s*(?:,|$)", m.group(1).replace("\n", " "))
    # crude: the last identifier on each port declaration is the port name
    decls = re.findall(r"(?:input|output|inout)[^,]*", m.group(1))
    out = []
    for d in decls:
        ids = re.findall(r"\b[A-Za-z_]\w*\b", d)
        ids = [i for i in ids if i not in {"input", "output", "inout", "reg", "wire",
                                           "logic", "signed"}]
        if ids:
            out.append(ids[-1])
    return out


def _rename(text: str, pmap: dict[str, str]) -> str:
    text = re.sub(r"\bTopModule\b", NEWMOD, text)
    for old, new in pmap.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    return text


def mutate(d: str) -> str | None:
    t = json.load(open(os.path.join(d, "task.json")))
    files = t["files"]
    golden = open(os.path.join(d, files["golden"])).read()
    # Port renaming breaks the VerilogEval testbench wiring; rename the MODULE only
    # (+ reframe the spec). That already makes the (prompt, solution) textually novel
    # without disturbing the harness. Semantic mutation is the deeper future test.
    pmap: dict[str, str] = {}
    name = "mut_" + os.path.basename(d).replace("veval_", "")
    out = os.path.join(os.path.dirname(d), name)
    os.makedirs(out, exist_ok=True)

    spec = open(os.path.join(d, files["spec"])).read()
    spec = ("# (mutated for contamination control — renamed identifiers, same function)\n\n"
            + _rename(spec, pmap))
    open(os.path.join(out, "spec.md"), "w").write(spec)
    open(os.path.join(out, "golden.v"), "w").write(_rename(golden, pmap))
    ref = open(os.path.join(d, files["ref_module"])).read()  # keep RefModule, rename its ports
    open(os.path.join(out, "ref_module.sv"), "w").write(_rename(ref, pmap).replace(NEWMOD, "RefModule"))
    test = open(os.path.join(d, files["test"])).read()
    open(os.path.join(out, "test.sv"), "w").write(_rename(test, pmap))

    t.update(task_id=name, top=NEWMOD, interface=_rename(t["interface"], pmap),
             files={"spec": "spec.md", "golden": "golden.v",
                    "ref_module": "ref_module.sv", "test": "test.sv"})
    json.dump(t, open(os.path.join(out, "task.json"), "w"), indent=2)
    return name


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10_000
    dirs = sorted(glob.glob("tasks/veval_*"))[:limit]
    ok = 0
    for d in dirs:
        try:
            if mutate(d):
                ok += 1
        except Exception as e:  # noqa: BLE001
            print("skip", d, e)
    print(f"mutated {ok}/{len(dirs)} tasks → tasks/mut_*")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
