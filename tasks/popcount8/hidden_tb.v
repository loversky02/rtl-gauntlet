// HIDDEN testbench — withheld. Exhaustive over all 256 inputs; expected value
// computed independently by summing the bits. R15: full coverage, incl. high byte
// and counts 5..8 the visible TB never touches.
`timescale 1ns/1ps
module tb_hidden;
  reg  [7:0] data;
  wire [3:0] count;
  reg  [3:0] exp;
  integer i, j;

  popcount8 dut(.data(data), .count(count));

  initial begin
    for (i=0; i<256; i=i+1) begin
      data = i[7:0]; #1;
      exp = 0;
      for (j=0; j<8; j=j+1) exp = exp + data[j];
      if (count !== exp) begin
        $display("RTLG_RESULT: FAIL (data=%b got=%0d exp=%0d)", data, count, exp);
        $finish;
      end
    end
    $display("RTLG_RESULT: PASS");
    $finish;
  end
endmodule
