"""BlackPill STM32F411 SPI1 (PA4 CS, PA5 SCK, PA6 MISO, PA7 MOSI; analyzers.json blackpill_spi1 channel
order) talking to a W25Q32JV at 12.5 MHz (APB2 100 MHz / 8), mode 0, written as a Logic 2 binary export.

Usage: python gen.py OUTDIR
"""
import sys
from pathlib import Path

import capfmt
import logicsim as ls

FLASH_DATA = b"BOXTEST!"


def main() -> int:
    out = Path(sys.argv[1])
    b = ls.Builder({"Channel 0": 1, "Channel 1": 0, "Channel 2": 1, "Channel 3": 0})
    txns = [(b"\x9f\0\0\0", b"\xff\xef\x40\x16"),            # JEDEC ID: Winbond, W25Q32
            (b"\x05\0", b"\xff\x00"),                          # read status register 1: not busy
            (b"\x03\x00\x10\x00" + bytes(8), bytes(4) + FLASH_DATA)]   # read 8 bytes at 0x001000
    ls.spi(b, txns, 12.5e6, mode=0, cs="Channel 0", clk="Channel 1", miso="Channel 2", mosi="Channel 3")
    files = capfmt.write_bin(b.digital(), out)
    print(f"wrote {len(files)} files in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
