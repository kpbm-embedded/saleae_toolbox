"""pytest: I2C transactions and Fast-mode timing of the Pico / BME280 captures."""
import os
from pathlib import Path

import capfmt
import decoders as dec

OUT = Path(os.environ["EX_OUT"])
OK = capfmt.load(OUT / "pico_i2c_ok.csv")
BAD = capfmt.load(OUT / "pico_i2c_bad.csv")


def compliant(d, mode: str = "fast") -> bool:
    f_max, t_low, t_high = dec.I2C_SPEC[mode]
    t = dec.i2c_timing(d, "GP5_SCL")
    return t["f_scl_hz"] <= f_max * 1.001 and t["t_low_min_s"] >= t_low and t["t_high_min_s"] >= t_high


def test_transactions() -> None:
    tx = dec.i2c_transactions(dec.i2c(OK, "GP5_SCL", "GP4_SDA"))
    assert tx[0] == {**tx[0], "addr": 0x77, "nak": True}
    assert (tx[1]["addr"], tx[1]["read"], tx[1]["data"]) == (0x76, False, [0xD0])
    assert (tx[2]["addr"], tx[2]["read"], tx[2]["data"]) == (0x76, True, [0x60])   # BME280 chip id
    assert (tx[3]["data"], tx[3]["nak"]) == ([0xF4, 0x27], False)


def test_fast_mode_timing() -> None:
    assert dec.i2c_timing(OK, "GP5_SCL")["f_scl_hz"] == 400_000
    assert compliant(OK)
    assert not compliant(BAD)                               # tLOW 1.0 us < 1.3 us
    assert dec.i2c_timing(BAD, "GP5_SCL")["t_low_min_s"] < 1.3e-6
