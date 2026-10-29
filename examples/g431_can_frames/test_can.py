"""pytest: classic CAN decode of the G431 FDCAN1 capture."""
import os
from pathlib import Path

import capfmt
import decoders as dec

D = capfmt.load(Path(os.environ["EX_OUT"]) / "g431_can.vcd")
F = dec.can(D, "FDCAN1_RX", 500_000)


def test_frames_ids_and_payload() -> None:
    assert len(F) == 4
    assert [(f["id"], f["extended"]) for f in F[:3]] == [(0x123, False), (0x18FF50E5, True), (0x700, False)]
    assert F[0]["data"] == [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88]
    assert F[1]["dlc"] == 4 and F[1]["data"] == [0x01, 0x7D, 0x00, 0xFF]
    assert F[2]["dlc"] == 0


def test_crc_and_ack() -> None:
    assert all(f["crc_ok"] and f["ack"] and not f["error"] for f in F[:3])


def test_stuff_error_detected() -> None:
    assert F[3]["error"] == "stuff" and not F[3]["crc_ok"]   # sent as 0x7FF; fields after the error are garbage


def test_bit_time_and_bus_load() -> None:
    ln = dec.line(D, "FDCAN1_RX")
    shortest = min(w for lv in (0, 1) for _, w in ln.pulses(lv))
    assert abs(shortest - 2e-6) < 1e-9                   # one bit at 500 kbit/s
    busy = sum(w for _, w in ln.pulses(0))
    load = busy / ln.t[-1]
    assert 0.1 < load < 0.9
