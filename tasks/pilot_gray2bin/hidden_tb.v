// HIDDEN testbench — withheld from the agent. Exhaustive over all 16 inputs,
// expected value computed independently in the bench (not a lookup the agent
// could have copied). R15: full coverage so the gap it reveals is real.
`timescale 1ns/1ps
module tb_hidden;
  reg  [3:0] gray;
  wire [3:0] bin;
  reg  [3:0] exp;
  integer i;

  gray2bin dut(.gray(gray), .bin(bin));

  initial begin
    for (i=0; i<16; i=i+1) begin
      gray = i[3:0]; #1;
      exp[3] = gray[3];
      exp[2] = gray[3] ^ gray[2];
      exp[1] = gray[3] ^ gray[2] ^ gray[1];
      exp[0] = gray[3] ^ gray[2] ^ gray[1] ^ gray[0];
      if (bin !== exp) begin
        $display("RTLG_RESULT: FAIL (gray=%b got=%b exp=%b)", gray, bin, exp);
        $finish;
      end
    end
    $display("RTLG_RESULT: PASS");
    $finish;
  end
endmodule
