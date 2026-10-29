"""pytest: quadrature count, glitch detection and the Logic 2 glitch filter that removes it."""
import os
from pathlib import Path

from saleae import automation

import capfmt
import decoders as dec

D = capfmt.load(Path(os.environ["EX_OUT"]) / "h743_encoder.vcd")
A, B = "PE9_TIM1_CH1", "PE11_TIM1_CH2"


def test_glitch_found() -> None:
    g = dec.glitches(D, A, 1e-6)
    assert len(g) == 1 and abs(g[0]["width_s"] - 80e-9) < 1e-9


def test_count_after_filter() -> None:
    clean = dec.deglitch(D, A, 1e-6)
    q = dec.quadrature(clean, A, B)
    assert q == {"count": 300, "illegal": 0, "reversals": 1}
    raw = dec.quadrature(D, A, B)
    assert raw["reversals"] > 1                               # the glitch looks like a back-and-forth


def test_glitch_filter_config() -> None:
    # what to set in Logic 2 (Device settings or automation) so the capture is already clean:
    # shortest real pulse is 20 us, the glitch 80 ns -> filter 1 us on both encoder channels
    real_min = min(w for lv in (0, 1) for t, w in dec.line(dec.deglitch(D, A, 1e-6), A).pulses(lv) if t > 0)  # t=0: capture start
    assert real_min >= 20e-6
    dev = automation.LogicDeviceConfiguration(enabled_digital_channels=[0, 1], digital_sample_rate=50_000_000,
                                              glitch_filters=[automation.GlitchFilterEntry(channel_index=c, pulse_width_seconds=1e-6) for c in (0, 1)])
    assert [g.pulse_width_seconds for g in dev.glitch_filters] == [1e-6, 1e-6]
