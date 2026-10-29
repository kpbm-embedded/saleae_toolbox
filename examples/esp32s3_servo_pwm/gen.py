"""ESP32-S3 LEDC timer 0, 50 Hz, 14-bit duty (1 tick = 20 ms / 16384 = 1.22 us) on GPIO4 driving a
hobby servo: 5 pulses each at 1.0 ms, 1.5 ms, 2.0 ms (duty set by ledc_set_duty, quantised to
ticks). Written as a Logic 2 binary export (digital_0.bin).

Usage: python gen.py OUTDIR
"""
import sys
from pathlib import Path

import capfmt
import logicsim as ls

PERIOD = 0.020
TICK = PERIOD / 16384
TARGETS = [1.0e-3, 1.5e-3, 2.0e-3]


def main() -> int:
    b = ls.Builder({"Channel 0": 0})
    for w in TARGETS:
        hi = round(w / TICK) * TICK
        for _ in range(5):
            b.set("Channel 0", 1); b.wait(hi); b.set("Channel 0", 0); b.wait(PERIOD - hi)
    capfmt.write_bin(b.digital(), Path(sys.argv[1]) / "export")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
