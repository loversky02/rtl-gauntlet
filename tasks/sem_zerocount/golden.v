// Semantic variant of the canonical popcount task: count ZERO bits (not ones).
// A model that memorized the canonical "count ones" solution is wrong here.
module zerocount8(input [7:0] data, output [3:0] count);
  assign count = (!data[0]) + (!data[1]) + (!data[2]) + (!data[3])
               + (!data[4]) + (!data[5]) + (!data[6]) + (!data[7]);
endmodule
