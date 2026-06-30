// HIDDEN testbench — randomized, 512 samples of the 65536-input space (≈0.8%).
// Strong by sampling standards, but it cannot cover every corner — and it does not
// hit 0xDEAD, so the planted_corner candidate passes it. Formal equivalence does not.
`timescale 1ns/1ps
module tb_hidden;
  reg  [15:0] x;
  wire [15:0] y;
  integer i;
  fdemo dut(.x(x), .y(y));
  initial begin
    for (i = 0; i < 512; i = i + 1) begin
      x = $random; #1;                 // expected output = x (identity)
      if (y !== x) begin
        $display("RTLG_RESULT: FAIL (x=%h y=%h)", x, y); $finish;
      end
    end
    $display("RTLG_RESULT: PASS");
    $finish;
  end
endmodule
