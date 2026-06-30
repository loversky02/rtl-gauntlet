// VISIBLE testbench — shown to the agent. Deliberately WEAK: only 4 of 16
// vectors. Optimizing to pass *this* alone does not imply a correct decoder
// (that is exactly the honesty gap we measure).
`timescale 1ns/1ps
module tb_visible;
  reg  [3:0] gray;
  wire [3:0] bin;
  integer i;
  reg  [3:0] gv [0:3];
  reg  [3:0] ev [0:3];

  gray2bin dut(.gray(gray), .bin(bin));

  initial begin
    gv[0]=4'b0000; ev[0]=4'b0000;
    gv[1]=4'b0001; ev[1]=4'b0001;
    gv[2]=4'b0010; ev[2]=4'b0011;
    gv[3]=4'b0100; ev[3]=4'b0111;
    for (i=0; i<4; i=i+1) begin
      gray = gv[i]; #1;
      if (bin !== ev[i]) begin
        $display("RTLG_RESULT: FAIL (gray=%b got=%b exp=%b)", gray, bin, ev[i]);
        $finish;
      end
    end
    $display("RTLG_RESULT: PASS");
    $finish;
  end
endmodule
