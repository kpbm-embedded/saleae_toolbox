"""Write a Logic 2 binary export channel: 1 kHz PWM, 30 % duty, 20 periods (fixture for @NAME@.rs)."""
import sys
from pathlib import Path

import capfmt
import logicsim as ls

b = ls.Builder({"Channel 0": 0})
ls.pwm(b, "Channel 0", 1000, 0.30, 20)
d = b.digital()
capfmt.write_bin_channel(d.channels["Channel 0"], Path(sys.argv[1]), capfmt.end_time(d))
