"""WeAct STM32H562 SWD (PA14 SWCLK, PA13 SWDIO) at 1 MHz, the sequence a probe sends on connect:
line reset, JTAG-to-SWD 0xE79E, line reset, idle, read DPIDR (0x6BA02477, Arm DP v2 for Cortex-M33),
write CTRL/STAT = 0x50000000 (CSYSPWRUPREQ|CDBGPWRUPREQ), read CTRL/STAT (0xF0000000: acks set),
AP read answered WAIT, then retried OK. Logic 2 CSV.

Usage: python gen.py OUTDIR
"""
import sys
from pathlib import Path

import capfmt
import logicsim as ls

JTAG_TO_SWD = [(0xE79E >> k) & 1 for k in range(16)]


def main() -> int:
    b = ls.Builder({"SWCLK_PA14": 0, "SWDIO_PA13": 0})
    ls.swd(b, [("reset",), ("bits", JTAG_TO_SWD), ("reset",), ("bits", [0, 0]),
               ("read", 0, 0x0, 0x6BA02477), ("write", 0, 0x4, 0x50000000), ("read", 0, 0x4, 0xF0000000),
               ("read", 1, 0xC, 0, 2), ("read", 1, 0xC, 0x24770011)],
           clk="SWCLK_PA14", dio="SWDIO_PA13")
    capfmt.write_csv(b.digital(), Path(sys.argv[1]) / "h562_swd.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
