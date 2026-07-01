# Spec: 8-bit population count (Hamming weight)

Implement a **combinational** module `popcount8` that outputs the number of bits set
to 1 in the 8-bit input.

## Locked interface (do not rename ports or change widths)

```verilog
module popcount8(input [7:0] data, output [3:0] count);
```

## Function (complete — determines the output for all 256 inputs)

`count` = the number of 1-bits in `data`, an integer in the range 0..8.
Formally: `count = data[0] + data[1] + ... + data[7]` (each term a 1-bit value).

## Requirements

- Purely combinational (no clock, no state).
- Synthesizable Verilog-2005.
- `count` is 4 bits wide because the maximum Hamming weight of 8 bits is 8.
- Correct for **all** 256 inputs — including high bits and counts 5..8, which a
  testbench you are shown may not exercise.
