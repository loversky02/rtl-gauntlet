"""Regression test for the SOUND X-aware + reset-settle equivalence oracle (A1).

Validates that the sound miter (scripts/sound_oracle_proto.py) replaces the paper's
hand-verified don't-care classification for 3 of the 4 flagged artifact tasks with a
machine-checked proof, catches genuinely-broken designs (non-vacuity), and documents
the one residual (circuit8, mixed-edge latch).

Skips cleanly when yosys or the (gitignored) task/candidate files are absent.
"""
from __future__ import annotations

import json
import os
import shutil
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

pytestmark = pytest.mark.skipif(shutil.which("yosys") is None, reason="yosys not on PATH")

try:
    import sound_oracle_proto as SO  # noqa: E402
except Exception:  # pragma: no cover
    SO = None


def _load(task):
    td = os.path.join(REPO, "tasks", f"veval_{task}")
    cand = os.path.join(REPO, "runs", "veval_gpt", f"veval_{task}", "candidate.v")
    if not (os.path.exists(td) and os.path.exists(cand)):
        pytest.skip(f"task/candidate for {task} not present (gitignored, regen via import_veval)")
    golden = open(os.path.join(td, "golden.v")).read()
    iface = json.load(open(os.path.join(td, "task.json")))["interface"]
    return golden, iface, open(cand).read()


@pytest.mark.parametrize("task,precond", [
    ("prob095_review2015_fsmshift", ""),          # init/reset transient, sync reset  -> automatic
    ("prob088_ece241_2014_q5b", ""),              # one-hot init, async reset          -> automatic
])
def test_init_transient_artifacts_prove_automatically(task, precond):
    assert SO is not None
    golden, iface, cand = _load(task)
    status, _ = SO.build(golden, cand, iface, os.path.join(REPO, "runs/xaware", task), precond_v=precond)
    assert status == "proven", f"{task} should prove equivalent (don't-care artifact), got {status}"


def test_input_sequence_precondition_artifact_proves():
    """prob149: proves equivalent only once the spec's gradual-level-change precondition is declared."""
    assert SO is not None
    golden, iface, cand = _load("prob149_ece241_2013_q4")
    status, _ = SO.build(golden, cand, iface, os.path.join(REPO, "runs/xaware/prob149"),
                         precond_v=SO.PRECOND_PROB149)
    assert status == "proven"


def test_non_vacuity_broken_designs_cex():
    """The sound oracle must still catch genuinely-wrong designs, not prove everything."""
    assert SO is not None
    golden, iface, base = _load("prob149_ece241_2013_q4")
    broken = base.replace("dfr = dfr_state;", "dfr = 1'b0;")
    assert base != broken, "fixture drift: dfr line not found"
    status, _ = SO.build(golden, broken, iface, os.path.join(REPO, "runs/xaware/broken"),
                         precond_v=SO.PRECOND_PROB149)
    assert status == "cex", "broken dfr must produce a counter-example"


def test_circuit8_mixed_edge_proves():
    """circuit8 (negedge FF + intentional latch): the real-latch half-cycle miter PROVES it
    (the old -nolatches build destroyed the latch and produced the last hand-verified CEX)."""
    from rtl_gauntlet.equiv import run_mixededge_equiv
    golden, _, cand = _load("prob145_circuit8")
    g = os.path.join(REPO, "tasks/veval_prob145_circuit8/golden.v")
    c = os.path.join(REPO, "runs/veval_gpt/veval_prob145_circuit8/candidate.v")
    r = run_mixededge_equiv(g, c, "TopModule", os.path.join(REPO, "runs/xaware/circuit8_me"), timeout=120)
    assert r.status == "careset_equiv", f"expected proof, got {r.status}"


def test_circuit8_mixed_edge_non_vacuous(tmp_path):
    """A wrong-edge candidate must still CEX under the mixed-edge miter."""
    from rtl_gauntlet.equiv import run_mixededge_equiv
    g = os.path.join(REPO, "tasks/veval_prob145_circuit8/golden.v")
    if not os.path.exists(g):
        pytest.skip("circuit8 golden not present")
    broken = tmp_path / "broken.v"
    broken.write_text(
        "module TopModule(input clock, input a, output reg p, output reg q);\n"
        "  always @(*) if (clock) p = a;\n"
        "  always @(posedge clock) q <= a;   // wrong edge\n"
        "endmodule\n")
    r = run_mixededge_equiv(g, str(broken), "TopModule",
                            os.path.join(REPO, "runs/xaware/circuit8_broken"), timeout=120)
    assert r.status == "cex", f"broken design must CEX, got {r.status}"


# --- Integration through the production oracle entry point (rtl_gauntlet.equiv.run_equiv) ---

def _paths(task, model="veval_gpt", cand="candidate.v"):
    g = os.path.join(REPO, "tasks", f"veval_{task}", "golden.v")
    c = os.path.join(REPO, "runs", model, f"veval_{task}", cand)
    if not (os.path.exists(g) and os.path.exists(c)):
        pytest.skip(f"golden/candidate for {task} not present (gitignored)")
    return g, c


@pytest.mark.parametrize("task,expected", [
    ("prob088_ece241_2014_q5b", "careset_equiv"),   # one-hot init — was hand-verified RHG_cex
    ("prob149_ece241_2013_q4", "careset_equiv"),     # gradual-change precond (from rtl_gauntlet/preconds/)
    ("prob145_circuit8", "careset_equiv"),           # mixed-edge — closed by the real-latch half-cycle miter
])
def test_run_equiv_resolves_flagged_artifacts(task, expected):
    from rtl_gauntlet.equiv import run_equiv
    g, c = _paths(task)
    r = run_equiv(g, c, "TopModule", os.path.join(REPO, "runs/integ", task), timeout=120)
    assert r.status == expected, f"{task}: expected {expected}, got {r.status}"


def test_run_equiv_non_vacuous_on_impossible_overfit():
    """The careset path must NOT falsely prove a genuine hack (the impossible-task hardcode)."""
    from rtl_gauntlet.equiv import run_equiv
    g = os.path.join(REPO, "tasks/impossible_popcount8/golden.v")
    c = os.path.join(REPO, "tasks/impossible_popcount8/planted_overfit.v")
    if not (os.path.exists(g) and os.path.exists(c)):
        pytest.skip("impossible_popcount8 not present")
    r = run_equiv(g, c, "popcount8", os.path.join(REPO, "runs/integ/impossible"), timeout=120)
    assert r.status == "cex", f"impossible overfit must stay cex, got {r.status}"
