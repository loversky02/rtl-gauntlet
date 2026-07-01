"""Prototype: a SOUND X-aware + reset-settle equivalence miter.

Recipe (validated empirically):
  gold0 = golden with setundef -zero -init   (x -> 0)
  gold1 = golden with setundef -one  -init   (x -> 1)
  gate  = candidate with setundef -zero -init
  care  = ~(gold0.out ^ gold1.out)     # bits where the two builds AGREE = defined = cared
  bad   = |((gold0.out ^ gate.out) & care)
  assert(!bad) only when `active` = (settled >= SETTLE cycles since last reset) AND precondition holds

This masks (a) output x-literal don't-cares and (b) init/reset-transient don't-cares AUTOMATICALLY.
Input-space / input-sequence preconditions (e.g. prob149 gradual level change) must be supplied
per task via `precond_v` (Verilog defining a wire `pre_ok`).
"""
from __future__ import annotations
import os, re, subprocess

DONTCARE_RE = re.compile(r"'[bodhBODH]?[0-9a-fA-F_xXzZ]*[xXzZ]")


def parse_ports(interface: str):
    """Return (inputs, outputs) as lists of (name, width) from a module header string."""
    body = interface[interface.find("(") + 1: interface.rfind(")")]
    ins, outs = [], []
    for raw in re.split(r",(?![^\[]*\])", body):
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"(input|output|inout)\s+(?:reg\s+|wire\s+|logic\s+|signed\s+)*(\[[^\]]*\]\s*)?(\w+)", line)
        if not m:
            continue
        d, rng, name = m.group(1), m.group(2), m.group(3)
        w = 1
        if rng:
            mm = re.search(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]", rng)
            if mm:
                w = abs(int(mm.group(1)) - int(mm.group(2))) + 1
        (ins if d == "input" else outs).append((name, w))
    return ins, outs


def _reset(ins):
    for name, _ in ins:
        low = name.lower()
        if "reset" in low or re.fullmatch(r"a?rst_?n?", low):
            active_low = low.endswith("n")
            return name, (0 if active_low else 1)
    return None, 1


def _clk(ins):
    for name, _ in ins:
        if name.lower() in ("clk", "clock"):
            return name
    return None


def build(golden: str, candidate: str, interface: str, wd: str,
          settle: int = 2, seq: int = 24, precond_v: str = "") -> tuple[str, bool]:
    """Returns (status, proven). status in {proven, cex, error}."""
    os.makedirs(wd, exist_ok=True)
    ins, outs = parse_ports(interface)
    clk, (rst, rstval) = _clk(ins), _reset(ins)

    def elab(src_file, mod, undef):
        # -nolatches: drive incomplete-case don't-cares instead of erroring on inferred latches
        return f"""read_verilog -sv -nolatches "{src_file}"
hierarchy -top TopModule
proc
async2sync
setundef -{undef} -init
opt -purge
rename TopModule {mod}
write_verilog -noattr "{wd}/{mod}.v"
design -reset
"""
    gpath = f"{wd}/golden.v"; cpath = f"{wd}/cand.v"
    open(gpath, "w").write(golden); open(cpath, "w").write(candidate)
    mk = elab(gpath, "gold0", "zero") + elab(gpath, "gold1", "one") + elab(cpath, "gate", "zero")
    r = subprocess.run(["yosys", "-p", mk], capture_output=True, text=True)
    if r.returncode != 0:
        return "error", False

    # port wiring for the three instances
    def conns(suffix):
        # inputs are SHARED (miter port); only outputs are per-instance
        return ", ".join(f".{n}({n})" for n, _ in ins) + ", " + \
               ", ".join(f".{n}({n}_{suffix})" for n, _ in outs)
    decls = "".join(f"  wire [{w-1}:0] {n}_0,{n}_1,{n}_g;\n" for n, w in outs)
    inwires = "".join(f"  wire [{w-1}:0] {n};\n" for n, w in ins) if False else ""
    ocat0 = "{" + ",".join(f"{n}_0" for n, _ in outs) + "}"
    ocat1 = "{" + ",".join(f"{n}_1" for n, _ in outs) + "}"
    ocatg = "{" + ",".join(f"{n}_g" for n, _ in outs) + "}"
    W = sum(w for _, w in outs)
    inports = ", ".join(f"input [{w-1}:0] {n}" if w > 1 else f"input {n}" for n, w in ins)
    rst_expr = rst if rst else "1'b0"
    since_reset = f"({rst_expr} == 1'b{rstval})" if rst else "1'b0"
    pre = precond_v if precond_v else "  wire pre_ok = 1'b1;\n"
    miter = f"""module miter({inports});
{decls}  gold0 u0({conns('0')});
  gold1 u1({conns('1')});
  gate  ug({conns('g')});
  wire [{W-1}:0] o0 = {ocat0};
  wire [{W-1}:0] o1 = {ocat1};
  wire [{W-1}:0] og = {ocatg};
  wire [{W-1}:0] care = ~(o0 ^ o1);
  wire bad = |((o0 ^ og) & care);
{pre}  reg [3:0] since;
  always @(posedge {clk}) since <= {since_reset} ? 4'd0 : ((since==4'd15) ? 4'd15 : since+4'd1);
  wire active = (since >= 4'd{settle}) && pre_ok;
  always @* if (active) assert(!bad);
endmodule
"""
    open(f"{wd}/miter.v", "w").write(miter)
    setat = f"-set-at 1 {rst} {rstval}" if rst else ""
    run = f"""read_verilog "{wd}/gold0.v" "{wd}/gold1.v" "{wd}/gate.v"
read_verilog -sv "{wd}/miter.v"
hierarchy -top miter
proc
flatten
async2sync
setundef -zero -init
opt
sat -seq {seq} {setat} -prove-asserts
"""
    r = subprocess.run(["yosys", "-p", run], capture_output=True, text=True)
    log = r.stdout + r.stderr
    if "no model found" in log.lower():
        return "proven", True
    if "model found" in log.lower():
        return "cex", False
    return "error", False


# prob149 spec precondition: thermometer-valid s AND water level changes by <=1 per cycle
# (reset establishes a known "low for a long time" level 0). Derived from the task testbench.
PRECOND_PROB149 = """  function [2:0] lvl(input [2:0] xx);
    lvl = (xx==3'b111) ? 3'd3 : (xx==3'b011) ? 3'd2 : (xx==3'b001) ? 3'd1 : (xx==3'b000) ? 3'd0 : 3'd7;
  endfunction
  wire [2:0] L = lvl(s);
  reg [2:0] Lprev; reg have_prev; reg pois;
  wire s_valid = (L != 3'd7);
  wire [2:0] dd = (L > Lprev) ? (L - Lprev) : (Lprev - L);
  wire grad = (have_prev == 1'b0) || (s_valid && (dd <= 3'd1));
  always @(posedge clk) begin
    pois      <= reset ? 1'b0 : (pois | ~s_valid | ~grad);
    Lprev     <= reset ? 3'd0 : (s_valid ? L : Lprev);
    have_prev <= reset ? 1'b1 : (have_prev | s_valid);
  end
  wire pre_ok = (pois == 1'b0) && s_valid && grad;
"""

if __name__ == "__main__":
    import json
    REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # (task, candidate-model-dir, precondition, note)
    CASES = [
        ("prob095_review2015_fsmshift", "veval_gpt", "", "init/reset-transient (sync reset)"),
        ("prob088_ece241_2014_q5b", "veval_gpt", "", "one-hot init (async reset)"),
        ("prob149_ece241_2013_q4", "veval_gpt", PRECOND_PROB149, "input-sequence precond (gradual)"),
        ("prob145_circuit8", "veval_gpt", "", "mixed-edge latch+negedge FF (HARD)"),
    ]
    print(f"{'task':32s} {'verdict':8s} note")
    print("-" * 78)
    for task, model, pre, note in CASES:
        td = f"{REPO}/tasks/veval_{task}"
        golden = open(f"{td}/golden.v").read()
        iface = json.load(open(f"{td}/task.json"))["interface"]
        candf = f"{REPO}/runs/{model}/veval_{task}/candidate.v"
        if not os.path.exists(candf):
            print(f"{task:32s} {'NO-CAND':8s} {candf}"); continue
        cand = open(candf).read()
        status, _ = build(golden, cand, iface, f"runs/xaware/{task}", precond_v=pre)
        mark = "OK-artifact" if status == "proven" else ("RESIDUAL" if status == "cex" else status)
        print(f"{task:32s} {status:8s} {note}  [{mark}]")

    # non-vacuity controls: deliberately-broken prob149 candidates MUST cex
    print("\nnon-vacuity controls (must CEX):")
    g149 = open(f"{REPO}/tasks/veval_prob149_ece241_2013_q4/golden.v").read()
    i149 = json.load(open(f"{REPO}/tasks/veval_prob149_ece241_2013_q4/task.json"))["interface"]
    base = open(f"{REPO}/runs/veval_gpt/veval_prob149_ece241_2013_q4/candidate.v").read()
    broken = {
        "dfr-forced-0": base.replace("dfr = dfr_state;", "dfr = 1'b0;"),
        "level3-wrong": base.replace("2'd3: begin\n        fr2 = 1'b0;\n        fr1 = 1'b0;\n        fr0 = 1'b0;",
                                     "2'd3: begin\n        fr2 = 1'b1;\n        fr1 = 1'b1;\n        fr0 = 1'b1;"),
    }
    for name, src in broken.items():
        status, _ = build(g149, src, i149, f"runs/xaware/broken_{name}", precond_v=PRECOND_PROB149)
        print(f"  {name:16s} -> {status}  [{'OK' if status=='cex' else 'LEAK!'}]")
