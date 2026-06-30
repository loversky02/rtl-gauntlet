// Curated golden reference — exhaustively correct Hamming weight.
module popcount8(input [7:0] data, output [3:0] count);
  assign count = data[0] + data[1] + data[2] + data[3]
               + data[4] + data[5] + data[6] + data[7];
endmodule
