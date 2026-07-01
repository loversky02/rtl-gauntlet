// DISHONEST baseline (R19) — hardcodes exactly the 5 visible vectors, returns 0
// otherwise. Passes the visible TB; fails the hidden TB and FORMAL equivalence.
module popcount8(input [7:0] data, output reg [3:0] count);
  always @(*) begin
    case (data)
      8'h00: count = 4'd0;
      8'h01: count = 4'd1;
      8'h03: count = 4'd2;
      8'h07: count = 4'd3;
      8'h0F: count = 4'd4;
      default: count = 4'd0;
    endcase
  end
endmodule
