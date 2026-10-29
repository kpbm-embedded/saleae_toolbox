"""K210 I2S0 (Sipeed Maix Bit: SCLK, WS, SD on FPIOA pins) as Philips I2S, 48 kHz, 16-bit stereo
(SCLK 1.536 MHz): a 1 kHz tone at -6 dBFS on the left channel, silence on the right (mono MEMS mic
with L/R select tied low). 4 ms of audio as VCD.

Usage: python gen.py OUTDIR
"""
import math
import sys
from pathlib import Path

import capfmt
import logicsim as ls

FS, F_TONE, AMP = 48_000, 1_000, 16384


def main() -> int:
    s = [(round(AMP * math.sin(2 * math.pi * F_TONE * n / FS)), 0) for n in range(FS * 4 // 1000)]
    b = ls.Builder({"I2S0_SCLK": 0, "I2S0_WS": 0, "I2S0_SD": 0})
    ls.i2s(b, s, FS, 16, sck="I2S0_SCLK", ws="I2S0_WS", sd="I2S0_SD")
    capfmt.write_vcd(b.digital(), Path(sys.argv[1]) / "k210_i2s.vcd")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
