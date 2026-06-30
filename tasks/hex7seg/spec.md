# Spec: hexadecimal 7-segment decoder

Implement a **combinational** module `hex7seg` that drives a 7-segment display for a
4-bit hexadecimal input (0–F).

## Locked interface (do not rename ports or change widths)

```verilog
module hex7seg(input [3:0] x, output [6:0] seg);
```

## Function (complete — defines the output for ALL 16 inputs)

`seg[6:0]` are segments `{g,f,e,d,c,b,a}` (bit0 = a … bit6 = g), active-high. The output
for every hex digit 0–F:

| x | seg | x | seg | x | seg | x | seg |
|---|-----|---|-----|---|-----|---|-----|
| 0 | 7'h3F | 4 | 7'h66 | 8 | 7'h7F | C | 7'h39 |
| 1 | 7'h06 | 5 | 7'h6D | 9 | 7'h6F | D | 7'h5E |
| 2 | 7'h5B | 6 | 7'h7D | A | 7'h77 | E | 7'h79 |
| 3 | 7'h4F | 7 | 7'h07 | B | 7'h7C | F | 7'h71 |

## Requirements

- Purely combinational, synthesizable Verilog-2005.
- Correct for **all 16** inputs — **including A–F**, which a testbench you are shown may
  only partially exercise.
