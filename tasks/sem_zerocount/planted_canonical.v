// The CANONICAL (memorized) popcount-ONES solution — WRONG for the count-zeros spec.
// It passes the balanced visible TB (where #ones == #zeros == 4) but fails the hidden
// TB and FORMAL equivalence: this is how a semantic mutation catches memorization.
module zerocount8(input [7:0] data, output [3:0] count);
  assign count = data[0] + data[1] + data[2] + data[3]
               + data[4] + data[5] + data[6] + data[7];
endmodule
