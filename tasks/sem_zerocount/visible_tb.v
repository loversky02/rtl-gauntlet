// VISIBLE testbench — only BALANCED inputs (#ones == #zeros == 4). For these, the
// memorized count-ones solution and the correct count-zeros both give 4, so the
// memorized solution passes here. The hidden/formal tiers expose it.
`timescale 1ns/1ps
module tb_visible;
  reg  [7:0] data;
  wire [3:0] count;
  reg  [7:0] dv [0:5];
  integer i;
  zerocount8 dut(.data(data), .count(count));
  initial begin
    dv[0]=8'h0F; dv[1]=8'hF0; dv[2]=8'h33; dv[3]=8'hCC; dv[4]=8'h55; dv[5]=8'hAA;
    for (i=0; i<6; i=i+1) begin
      data = dv[i]; #1;
      if (count !== 4'd4) begin
        $display("RTLG_RESULT: FAIL (data=%b got=%0d exp=4)", data, count); $finish;
      end
    end
    $display("RTLG_RESULT: PASS"); $finish;
  end
endmodule
