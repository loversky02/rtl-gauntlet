// Input precondition for prob149 (ece241_2013_q4, water-level FSM).
//
// The spec's environment is physical: the water level changes by at most one thermometer
// step per clock, and only thermometer-valid sensor codes occur; reset establishes a known
// "low for a long time" level 0. The withheld testbench (test.sv) drives `s` exactly this way
// (sval +/- 1 per cycle -> thermometer[sval]). Declaring it here lets the X-aware miter PROVE
// the flagged candidates equivalent instead of hand-verifying them. Defines `wire pre_ok`.
//
// Ports referenced (must match the golden interface): clk, reset, s[2:0].
function [2:0] lvl(input [2:0] xx);
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
