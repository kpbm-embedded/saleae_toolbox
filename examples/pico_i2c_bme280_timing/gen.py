"""Pico RP2040 I2C0 (GP4 SDA, GP5 SCL) at 400 kHz: probe 0x77 (no device, NAK), then the BME280 at
0x76: read chip id 0xD0 (= 0x60), write ctrl_meas 0xF4 = 0x27. Two captures as Logic 2 CSV:
  pico_i2c_ok.csv   tLOW 1.4 us, tHIGH 1.1 us   (meets Fast mode: tLOW >= 1.3 us, tHIGH >= 0.6 us)
  pico_i2c_bad.csv  tLOW 1.0 us, tHIGH 1.5 us   (same 400 kHz, tLOW too short: what a wrong duty gives)

Usage: python gen.py OUTDIR
"""
import sys
from pathlib import Path

import capfmt
import logicsim as ls

OPS = [("w", 0x77, b"", 0), ("w", 0x76, b"\xd0"), ("r", 0x76, b"\x60"), ("w", 0x76, b"\xf4\x27")]


def capture(t_low: float, t_high: float) -> ls.Digital:
    b = ls.Builder({"GP5_SCL": 1, "GP4_SDA": 1})
    ls.i2c(b, OPS[:1], scl="GP5_SCL", sda="GP4_SDA", t_low=t_low, t_high=t_high)
    ls.i2c(b, OPS[1:3], scl="GP5_SCL", sda="GP4_SDA", t_low=t_low, t_high=t_high)
    ls.i2c(b, OPS[3:], scl="GP5_SCL", sda="GP4_SDA", t_low=t_low, t_high=t_high)
    return b.digital()


def main() -> int:
    out = Path(sys.argv[1])
    capfmt.write_csv(capture(1.4e-6, 1.1e-6), out / "pico_i2c_ok.csv")
    capfmt.write_csv(capture(1.0e-6, 1.5e-6), out / "pico_i2c_bad.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
