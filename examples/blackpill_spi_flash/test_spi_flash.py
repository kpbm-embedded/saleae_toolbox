"""pytest: decode the BlackPill SPI1 / W25Q32 capture (Logic 2 binary export) and check timing."""
import os
from pathlib import Path

import capfmt
import decoders as dec

D = capfmt.load(Path(os.environ["EX_OUT"]) / "export")
T = dec.spi(D, "Channel 1", "Channel 3", "Channel 2", "Channel 0", mode=0)


def test_three_transactions_whole_bytes() -> None:
    assert len(T) == 3 and all(t["partial_bits"] == 0 for t in T)


def test_jedec_id_is_winbond_w25q32() -> None:
    assert T[0]["mosi"][0] == 0x9F and T[0]["miso"][1:] == [0xEF, 0x40, 0x16]


def test_read_data() -> None:
    assert T[1]["miso"][1] & 1 == 0                       # BUSY clear before the read
    assert T[2]["mosi"][:4] == [0x03, 0x00, 0x10, 0x00]
    assert bytes(T[2]["miso"][4:]) == b"BOXTEST!"


def test_clock_rate_and_cs_setup() -> None:
    clk = dec.line(D, "Channel 1").edges(rising=True)
    period = min(b - a for a, b in zip(clk, clk[1:]))
    assert abs(1 / period - 12.5e6) / 12.5e6 < 0.01
    cs_fall = dec.line(D, "Channel 0").edges(rising=False)[0]
    first = next(t for t in clk if t > cs_fall)
    assert first - cs_fall >= period / 2                   # W25Q tSLCH 5 ns; SPI1 gives half a clock
