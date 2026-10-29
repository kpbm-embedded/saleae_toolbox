"""pytest: GPIO response latency vs a 100 us budget, and the capture in four file formats."""
import os
from pathlib import Path

import pytest

import capfmt
import decoders as dec
from gen import OUTLIER_AT

OUT = Path(os.environ["EX_OUT"])
D = capfmt.load(OUT / "gpio.csv")
BUDGET = 100e-6


def pct(xs: list[float], p: float) -> float:
    s = sorted(xs)
    return s[min(len(s) - 1, int(p / 100 * len(s)))]


def test_latency_stats() -> None:
    lat = dec.latency(D, "GPIO17_IN", "GPIO27_OUT")
    assert len(lat) == 200
    assert 35e-6 <= pct(lat, 50) <= 60e-6 and pct(lat, 99) <= BUDGET
    over = [i for i, x in enumerate(lat) if x > BUDGET]
    assert over == [OUTLIER_AT]                               # one miss: report it, do not hide it


@pytest.mark.parametrize("name,rate", [("gpio.vcd", 0), ("gpio_bin", 0), ("gpio.sr", 10_000_000)])
def test_round_trip(name: str, rate: int) -> None:
    capfmt.save(D, OUT / name, rate)
    e = capfmt.load(OUT / name)
    a, b = list(e.channels)
    lat2 = dec.latency(e, a, b)
    ref = dec.latency(D, "GPIO17_IN", "GPIO27_OUT")
    tol = 2 / rate if rate else 1e-9                          # .sr: edges move to the 100 ns grid
    assert len(lat2) == len(ref) and max(abs(x - y) for x, y in zip(lat2, ref)) <= tol
