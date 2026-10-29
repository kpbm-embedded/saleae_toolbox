"""CH32V003 PD6 as 1-Wire master (open drain + 4.7k pull-up) talking to one DS18B20, standard speed:
reset/presence, Read ROM 0x33 (8 bytes, family 0x28, CRC8), Skip ROM + Convert T 0xCC 0x44,
Skip ROM + Read Scratchpad 0xCC 0xBE (9 bytes, 0x0191 = 25.0625 C). ds18b20_absent.csv: no presence.

Usage: python gen.py OUTDIR
"""
import sys
from pathlib import Path

import capfmt
import logicsim as ls

ROM7 = bytes([0x28, 0xFF, 0x4C, 0x1E, 0x61, 0x16, 0x04])
SCRATCH8 = bytes([0x91, 0x01, 0x4B, 0x46, 0x7F, 0xFF, 0x0F, 0x10])


def main() -> int:
    out = Path(sys.argv[1])
    rom = ROM7 + bytes([ls.crc8_maxim(ROM7)])
    scratch = SCRATCH8 + bytes([ls.crc8_maxim(SCRATCH8)])
    b = ls.Builder({"PD6": 1})
    ls.ow_reset(b, "PD6"); ls.ow_bytes(b, "PD6", b"\x33" + rom)
    ls.ow_reset(b, "PD6"); ls.ow_bytes(b, "PD6", b"\xcc\x44"); b.wait(750e-6)
    ls.ow_reset(b, "PD6"); ls.ow_bytes(b, "PD6", b"\xcc\xbe" + scratch)
    capfmt.write_csv(b.digital(), out / "ds18b20.csv")
    b = ls.Builder({"PD6": 1})
    ls.ow_reset(b, "PD6", presence=False)
    capfmt.write_csv(b.digital(), out / "ds18b20_absent.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
