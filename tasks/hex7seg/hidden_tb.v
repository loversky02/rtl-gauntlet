// HIDDEN testbench — withheld. Exhaustive over all 16 hex digits, incl. A-F.
`timescale 1ns/1ps
module tb_hidden;
  reg  [3:0] x;
  wire [6:0] seg;
  reg  [6:0] ev [0:15];
  integer i;
  hex7seg dut(.x(x), .seg(seg));
  initial begin
    ev[0]=7'h3F; ev[1]=7'h06; ev[2]=7'h5B; ev[3]=7'h4F; ev[4]=7'h66; ev[5]=7'h6D; ev[6]=7'h7D; ev[7]=7'h07;
    ev[8]=7'h7F; ev[9]=7'h6F; ev[10]=7'h77; ev[11]=7'h7C; ev[12]=7'h39; ev[13]=7'h5E; ev[14]=7'h79; ev[15]=7'h71;
    for (i=0; i<16; i=i+1) begin
      x = i[3:0]; #1;
      if (seg !== ev[i]) begin
        $display("RTLG_RESULT: FAIL (x=%h got=%h exp=%h)", x, seg, ev[i]); $finish;
      end
    end
    $display("RTLG_RESULT: PASS"); $finish;
  end
endmodule
