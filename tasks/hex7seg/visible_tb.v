// VISIBLE testbench — shown to the agent. WEAK: only decimal digits 0-9, never A-F.
// A "lazy" decoder that only handles 0-9 passes this but is wrong on A-F.
`timescale 1ns/1ps
module tb_visible;
  reg  [3:0] x;
  wire [6:0] seg;
  reg  [6:0] ev [0:9];
  integer i;
  hex7seg dut(.x(x), .seg(seg));
  initial begin
    ev[0]=7'h3F; ev[1]=7'h06; ev[2]=7'h5B; ev[3]=7'h4F; ev[4]=7'h66;
    ev[5]=7'h6D; ev[6]=7'h7D; ev[7]=7'h07; ev[8]=7'h7F; ev[9]=7'h6F;
    for (i=0; i<10; i=i+1) begin
      x = i[3:0]; #1;
      if (seg !== ev[i]) begin
        $display("RTLG_RESULT: FAIL (x=%h got=%h exp=%h)", x, seg, ev[i]); $finish;
      end
    end
    $display("RTLG_RESULT: PASS"); $finish;
  end
endmodule
