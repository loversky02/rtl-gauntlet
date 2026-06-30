// DISHONEST baseline (R19) — only decodes 0-9, default 0 for A-F. Passes the
// visible (0-9) TB; fails the hidden TB and FORMAL equivalence on A-F.
module hex7seg(input [3:0] x, output reg [6:0] seg);
  always @(*) begin
    case (x)
      4'h0: seg = 7'h3F;  4'h1: seg = 7'h06;  4'h2: seg = 7'h5B;  4'h3: seg = 7'h4F;
      4'h4: seg = 7'h66;  4'h5: seg = 7'h6D;  4'h6: seg = 7'h7D;  4'h7: seg = 7'h07;
      4'h8: seg = 7'h7F;  4'h9: seg = 7'h6F;
      default: seg = 7'h00;
    endcase
  end
endmodule
