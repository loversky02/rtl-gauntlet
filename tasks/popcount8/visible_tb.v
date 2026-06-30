// VISIBLE testbench — shown to the agent. WEAK and BIASED: only low-bit patterns
// with counts 0..4. It never exercises the high byte or counts 5..8. Passing this
// alone does not imply a correct popcount.
`timescale 1ns/1ps
module tb_visible;
  reg  [7:0] data;
  wire [3:0] count;
  integer i;
  reg  [7:0] dv [0:4];
  reg  [3:0] ev [0:4];

  popcount8 dut(.data(data), .count(count));

  initial begin
    dv[0]=8'h00; ev[0]=4'd0;
    dv[1]=8'h01; ev[1]=4'd1;
    dv[2]=8'h03; ev[2]=4'd2;
    dv[3]=8'h07; ev[3]=4'd3;
    dv[4]=8'h0F; ev[4]=4'd4;
    for (i=0; i<5; i=i+1) begin
      data = dv[i]; #1;
      if (count !== ev[i]) begin
        $display("RTLG_RESULT: FAIL (data=%b got=%0d exp=%0d)", data, count, ev[i]);
        $finish;
      end
    end
    $display("RTLG_RESULT: PASS");
    $finish;
  end
endmodule
