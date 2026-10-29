"""Yocto image on an SoC board (Raspberry Pi 4 with meta-raspberrypi, or an i.MX8M Mini EVK): a
libgpiod program waits for a rising edge on GPIO17 and drives GPIO27 high, then low again with the
input. 200 stimulus pulses at 1 kHz; latency 35-60 us (pseudo-random, seed fixed) and one 180 us
outlier (a scheduling hiccup without PREEMPT_RT). Logic 2 CSV.

Usage: python gen.py OUTDIR
"""
import random
import sys
from pathlib import Path

import capfmt
import logicsim as ls

OUTLIER_AT = 137


def main() -> int:
    rnd = random.Random(29)
    b = ls.Builder({"GPIO17_IN": 0, "GPIO27_OUT": 0})
    for i in range(200):
        lat = 180e-6 if i == OUTLIER_AT else rnd.uniform(35e-6, 60e-6)
        b.set("GPIO17_IN", 1); b.wait(lat); b.set("GPIO27_OUT", 1)
        b.wait(400e-6 - lat); b.set("GPIO17_IN", 0); b.wait(lat); b.set("GPIO27_OUT", 0); b.wait(600e-6 - lat)
    capfmt.write_csv(b.digital(), Path(sys.argv[1]) / "gpio.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
