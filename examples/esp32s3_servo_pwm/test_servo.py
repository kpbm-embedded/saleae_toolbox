"""pytest: servo PWM from an ESP32-S3 LEDC capture; the assertions a HIL test would make."""
import os
from pathlib import Path

import capfmt
import decoders as dec
from gen import TARGETS, TICK

D = capfmt.load(Path(os.environ["EX_OUT"]) / "export")
HIGHS = [w for _, w in dec.line(D, "Channel 0").pulses(1)]


def test_period_50hz() -> None:
    p = dec.pwm(D, "Channel 0")
    assert p["cycles"] == 14 and abs(p["freq_hz"] - 50) < 0.05
    assert p["jitter_pp_s"] < 1e-6


def test_pulse_widths_within_one_tick() -> None:
    assert len(HIGHS) == 15
    for i, w in enumerate(HIGHS):
        assert abs(w - TARGETS[i // 5]) <= TICK


def test_servo_range() -> None:
    assert 0.9e-3 <= min(HIGHS) and max(HIGHS) <= 2.1e-3   # stay inside the servo's 0.9-2.1 ms range
