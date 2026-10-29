"""Pico 2 (RP2350) I2C1 (GP6 SDA, GP7 SCL) at 100 kHz with a BME280 at 0x76: soft reset, read id,
write ctrl_meas (forced mode, x1), read 3 temperature bytes. Every access ends with STOP (pico-sdk
i2c_write_blocking(nostop=false)). Logic 2 CSV.

Usage: python gen.py OUTDIR
"""
import sys
from pathlib import Path

import capfmt
import logicsim as ls

SEQ = [[("w", 0x76, b"\xe0\xb6")], [("w", 0x76, b"\xd0")], [("r", 0x76, b"\x60")],
       [("w", 0x76, b"\xf4\x25")], [("w", 0x76, b"\xfa")], [("r", 0x76, b"\x7e\xed\x00")]]


def main() -> int:
    b = ls.Builder({"GP7_SCL": 1, "GP6_SDA": 1})
    for ops in SEQ:
        ls.i2c(b, ops, 100e3, scl="GP7_SCL", sda="GP6_SDA")
    capfmt.write_csv(b.digital(), Path(sys.argv[1]) / "pico2_i2c.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
