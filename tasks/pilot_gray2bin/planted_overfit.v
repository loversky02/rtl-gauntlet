// DISHONEST baseline (R19) — does NOT implement the spec. It hardcodes exactly
// the 4 visible vectors and returns 0 otherwise. By construction it PASSES the
// visible TB while FAILING the hidden TB and FORMAL equivalence. Used to prove
// the oracle actually catches over-fitting (not the LLM — scored directly).
module gray2bin(input [3:0] gray, output reg [3:0] bin);
  always @(*) begin
    case (gray)
      4'b0000: bin = 4'b0000;
      4'b0001: bin = 4'b0001;
      4'b0010: bin = 4'b0011;
      4'b0100: bin = 4'b0111;
      default: bin = 4'b0000;
    endcase
  end
endmodule
