"""pytest: WS2812 decode + timing windows on sigrok .sr captures."""
import os
from pathlib import Path

import capfmt
import decoders as dec
from gen import PIXELS

OUT = Path(os.environ["EX_OUT"])


def test_pixels_ok() -> None:
    r = dec.ws2812(capfmt.load(OUT / "ws2812_ok.sr"), "P0_06")
    assert r["frames"] == [PIXELS] and r["violations"] == []


def test_reset_gap() -> None:
    d = capfmt.load(OUT / "ws2812_ok.sr")
    lows = [w for _, w in dec.line(d, "P0_06").pulses(0)]
    assert max(lows) >= 50e-6                                # latch: reset >= 50 us before the frame


def test_t0h_too_long_is_flagged() -> None:
    r = dec.ws2812(capfmt.load(OUT / "ws2812_bad.sr"), "P0_06")
    assert len(r["violations"]) > 0 and "outside T0H/T1H" in r["violations"][0]
