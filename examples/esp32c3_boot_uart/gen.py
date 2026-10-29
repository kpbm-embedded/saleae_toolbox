"""ESP32-C3 U0TXD (GPIO21) at 115200 8N1: the first lines of the ROM boot log, with two 100 ns
glitches (crosstalk from a USB cable next to the probe lead). Logic 2 CSV.

Usage: python gen.py OUTDIR
"""
import sys
from pathlib import Path

import capfmt
import logicsim as ls

TEXT = b"ESP-ROM:esp32c3-api1-20210207\r\nBuild:Feb  7 2021\r\nrst:0x1 (POWERON),boot:0xc (SPI_FAST_FLASH_BOOT)\r\n"


def main() -> int:
    b = ls.Builder({"U0TXD": 1}, lead=50e-6)
    ls.uart(b, "U0TXD", 115200, TEXT)
    bit = 1 / 115200
    # each glitch sits on a UART sample point (bit centre), so it changes what a decoder reads
    ls.glitch(b, "U0TXD", 50e-6 + 11 * bit * 3 + 4.5 * bit - 50e-9, 100e-9)   # data bit 3 of byte 3
    ls.glitch(b, "U0TXD", 50e-6 + 11 * bit * 40 + 9.5 * bit - 50e-9, 100e-9)  # stop bit of byte 40
    capfmt.write_csv(b.digital(), Path(sys.argv[1]) / "esp32c3_boot.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
