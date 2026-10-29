"""WeAct STM32G431 FDCAN1 RX (PA11, logic side of the transceiver) at 500 kbit/s, classic frames:
0x123 (8 bytes), J1939-style extended 0x18FF50E5, a 0-byte heartbeat 0x700, and one frame with a
broken bit-stuffing (as a faulty node or a bad sample point would show). Written as VCD.

Usage: python gen.py OUT.vcd
"""
import sys
from pathlib import Path

import capfmt
import logicsim as ls

FRAMES = [(0x123, bytes([0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88]), False),
          (0x18FF50E5, bytes([0x01, 0x7D, 0x00, 0xFF]), True),
          (0x700, b"", False)]


def main() -> int:
    b = ls.Builder({"FDCAN1_RX": 1}, lead=30e-6)
    for ident, data, ext in FRAMES:
        ls.can(b, "FDCAN1_RX", 500_000, ident, data, extended=ext)
        b.wait(40e-6)
    ls.can(b, "FDCAN1_RX", 500_000, 0x7FF, b"\0\0\0", break_stuffing=True)
    b.wait(100e-6)
    capfmt.write_vcd(b.digital(), Path(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
