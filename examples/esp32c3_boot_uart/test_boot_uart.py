"""pytest: glitches on the ESP32-C3 boot UART: find them, see the damage, filter, decode exactly."""
import os
from pathlib import Path

import capfmt
import decoders as dec
from gen import TEXT

D = capfmt.load(Path(os.environ["EX_OUT"]) / "esp32c3_boot.csv")


def test_two_glitches() -> None:
    g = dec.glitches(D, "U0TXD", 2e-6)
    assert len(g) == 2 and all(abs(x["width_s"] - 100e-9) < 1e-9 for x in g)


def test_raw_decode_is_damaged() -> None:
    fr = dec.uart(D, "U0TXD", 115200)
    raw = bytes(f["data"] for f in fr)
    assert raw[3] != TEXT[3] and raw[:3] == TEXT[:3]
    assert fr[40]["error"] == "framing"


def test_filtered_decode_and_autobaud() -> None:
    clean = dec.deglitch(D, "U0TXD", 2e-6)
    assert dec.estimate_baud(clean, "U0TXD") == 115200
    fr = dec.uart(clean, "U0TXD", 115200)
    assert bytes(f["data"] for f in fr) == TEXT and not any(f["error"] for f in fr)
    assert b"rst:0x1 (POWERON)" in TEXT
