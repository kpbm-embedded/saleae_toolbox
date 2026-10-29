"""Raspberry Pi Pico (RP2040) SPI0 to an SD card at 400 kHz (card init speed), mode 0: CS high with
80 dummy clocks is skipped here; CMD0 = 40 00 00 00 00 95 with CS low. Written as a Logic 2 binary
export (digital_0.bin CS GP17, digital_1.bin SCK GP18, digital_2.bin MOSI GP19, digital_3.bin MISO GP16).

Usage: python gen.py OUTDIR
"""
import sys
from pathlib import Path

import capfmt
import logicsim as ls


def main() -> int:
    b = ls.Builder({"CS": 1, "SCK": 0, "MOSI": 1, "MISO": 1})
    ls.spi(b, [(bytes([0x40, 0, 0, 0, 0, 0x95, 0xFF]), bytes([0xFF] * 6 + [0x01]))], 400e3, 0,
           clk="SCK", mosi="MOSI", miso="MISO", cs="CS")
    capfmt.write_bin(b.digital(), Path(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
