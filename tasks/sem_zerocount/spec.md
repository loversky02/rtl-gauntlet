# Spec: count the ZERO bits

Implement a **combinational** module `zerocount8` that outputs the number of bits that are
**0** in the 8-bit input.

## Locked interface
```verilog
module zerocount8(input [7:0] data, output [3:0] count);
```

## Function (complete, all 256 inputs)
`count` = number of bits of `data` equal to 0 (range 0..8). Equivalently
`count = 8 - (number of 1 bits)`. Note: this counts **zeros**, not ones.

## Requirements
- Purely combinational, synthesizable Verilog-2005.
- Correct for all 256 inputs.
