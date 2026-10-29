"""pytest: I2S decode of the K210 capture: sample rate, tone frequency, level, silent channel."""
import math
import os
from pathlib import Path

import capfmt
import decoders as dec

D = capfmt.load(Path(os.environ["EX_OUT"]) / "k210_i2s.vcd")
S = dec.i2s(D, "I2S0_SCLK", "I2S0_WS", "I2S0_SD", 16)


def test_sample_rate() -> None:
    ws = dec.line(D, "I2S0_WS").edges(rising=False)
    fs = 1 / ((ws[-1] - ws[0]) / (len(ws) - 1))
    assert abs(fs - 48_000) < 1


def test_tone() -> None:
    left = [l for l, _ in S]
    assert len(left) >= 190
    ups = [i for i in range(1, len(left)) if left[i - 1] < 0 <= left[i]]
    f = 48_000 / ((ups[-1] - ups[0]) / (len(ups) - 1))
    assert abs(f - 1000) < 5
    rms = math.sqrt(sum(x * x for x in left) / len(left))
    assert abs(20 * math.log10(rms * math.sqrt(2) / 32768) - (-6.02)) < 0.2   # -6 dBFS peak


def test_right_silent() -> None:
    assert all(r == 0 for _, r in S)
