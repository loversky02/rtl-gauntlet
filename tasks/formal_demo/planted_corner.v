// Candidate that is correct EXCEPT on the single input 0xDEAD. A randomized hidden
// testbench (few hundred of 65536 inputs) almost surely misses 0xDEAD → it passes;
// exhaustive FORMAL equivalence catches it. This is "formal earns its keep": formal
// finds what a finite (even randomized) test suite cannot.
module fdemo(input [15:0] x, output [15:0] y);
  assign y = (x == 16'hDEAD) ? 16'h0000 : x;
endmodule
