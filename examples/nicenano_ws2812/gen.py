"""nice!nano (nRF52840) P0.06 -> WS2812B strip of 4 LEDs, generated like the nRF PWM peripheral does
it (16 MHz base clock, 20 ticks = 1.25 us per bit; '0' = 6 ticks 375 ns high, '1' = 13 ticks 812.5 ns).
ws2812_bad.sr uses 10 ticks (625 ns) for '0', outside the WS2812B T0H window (220-380 ns typ, here
checked as 250-550 ns). Both written as sigrok .sr at 20 MHz.

Usage: python gen.py OUTDIR
"""
import sys
from pathlib import Path

import capfmt
import logicsim as ls

PIXELS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (16, 32, 48)]
TICK = 1 / 16e6


def capture(t0h_ticks: int) -> ls.Digital:
    b = ls.Builder({"P0_06": 0})
    ls.ws2812(b, "P0_06", PIXELS, t0h=t0h_ticks * TICK, t1h=13 * TICK, period=20 * TICK)
    return b.digital()


def main() -> int:
    out = Path(sys.argv[1])
    capfmt.write_sr(capture(6), out / "ws2812_ok.sr", 20_000_000)
    capfmt.write_sr(capture(10), out / "ws2812_bad.sr", 20_000_000)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
