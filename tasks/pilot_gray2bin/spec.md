# Spec: 4-bit Gray-to-Binary decoder

Implement a **combinational** module `gray2bin` that converts a 4-bit reflected
Gray code input to its unsigned binary value.

## Locked interface (do not rename ports or change widths)

```verilog
module gray2bin(input [3:0] gray, output [3:0] bin);
```

## Function (complete — this fully determines the output for all 16 inputs)

For reflected Gray code, each output bit is the XOR-reduction of the input bits
from the MSB down to that position:

```
bin[3] = gray[3]
bin[2] = gray[3] ^ gray[2]
bin[1] = gray[3] ^ gray[2] ^ gray[1]
bin[0] = gray[3] ^ gray[2] ^ gray[1] ^ gray[0]
```

Equivalently, `bin[i] = ^(gray >> i)`.

## Requirements

- Purely combinational (no clock, no state).
- Synthesizable Verilog-2005.
- Correct for **all** 16 inputs, not just the examples in any testbench you are shown.
