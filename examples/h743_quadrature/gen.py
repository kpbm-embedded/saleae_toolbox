"""WeAct STM32H743 TIM1 in encoder mode (PE9 = CH1/A, PE11 = CH2/B): a motor turns 400 quarter steps
forward at 20 us per step, then 100 back; one 80 ns glitch on A (EMI from the motor driver). VCD.

Usage: python gen.py OUTDIR
"""
import sys
from pathlib import Path

import capfmt
import logicsim as ls


def main() -> int:
    b = ls.Builder({"PE9_TIM1_CH1": 0, "PE11_TIM1_CH2": 0})
    ls.quadrature(b, [1] * 400 + [-1] * 100, 20e-6, a="PE9_TIM1_CH1", bch="PE11_TIM1_CH2")
    ls.glitch(b, "PE9_TIM1_CH1", 3.005e-3, 80e-9)
    capfmt.write_vcd(b.digital(), Path(sys.argv[1]) / "h743_encoder.vcd")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
