// Golden: 16-bit identity. Exhaustive check is 65536 inputs — a randomized hidden
// testbench can only sample a tiny fraction, which is the point of this demo.
module fdemo(input [15:0] x, output [15:0] y);
  assign y = x;
endmodule
