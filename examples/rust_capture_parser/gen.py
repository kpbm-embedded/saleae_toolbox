"""BlackPill STM32F411 USART2 TX (PA2) at 115200 sending "hello rust\\r\\n", written as one Logic 2
binary export channel file (fixture_uart.bin) for the Rust parser's tests.

Usage: python gen.py OUTDIR
"""
import sys
from pathlib import Path

import capfmt
import logicsim as ls


def main() -> int:
    b = ls.Builder({"Channel 0": 1})
    ls.uart(b, "Channel 0", 115200, b"hello rust\r\n")
    d = b.digital()
    capfmt.write_bin_channel(d.channels["Channel 0"], Path(sys.argv[1]) / "fixture_uart.bin", capfmt.end_time(d) + 1e-4)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
