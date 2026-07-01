module counter8(input clk, input rst, input en, output reg [7:0] q);
  always @(posedge clk)
    if (rst)      q <= 8'd0;
    else if (en)  q <= q + 8'd1;
endmodule
