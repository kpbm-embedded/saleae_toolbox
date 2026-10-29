"""Write a Logic 2 binary export channel: a 10 kHz clock with three 40 ns glitches (fixture for @NAME@.zig)."""
import sys
from pathlib import Path

import capfmt
import logicsim as ls

b = ls.Builder({"Channel 0": 0})
ls.pwm(b, "Channel 0", 10e3, 0.5, 30)
for at in (0.55e-3, 1.27e-3, 2.01e-3):
    ls.glitch(b, "Channel 0", at, 40e-9)
d = b.digital()
capfmt.write_bin_channel(d.channels["Channel 0"], Path(sys.argv[1]), capfmt.end_time(d))
