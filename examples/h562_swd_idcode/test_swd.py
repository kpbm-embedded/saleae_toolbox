"""pytest: SWD decode of the H562 connect sequence."""
import os
from pathlib import Path

import capfmt
import decoders as dec

OPS = [o for o in dec.swd(capfmt.load(Path(os.environ["EX_OUT"]) / "h562_swd.csv"), "SWCLK_PA14", "SWDIO_PA13")
       if o["op"] != "line_reset"]


def test_dpidr() -> None:
    o = OPS[0]
    assert (o["op"], o["apndp"], o["addr"], o["ack"]) == ("read", "DP", 0x0, "OK") and o["parity_ok"]
    v = o["data"]
    assert (v >> 1) & 0x7FF == 0x23B                          # designer: Arm (JEP106 0x23B)
    assert (v >> 12) & 0xF == 2                               # DP architecture version 2


def test_power_up_handshake() -> None:
    assert (OPS[1]["op"], OPS[1]["addr"], OPS[1]["data"]) == ("write", 0x4, 0x50000000)
    assert OPS[2]["data"] >> 28 == 0xF                         # CSYSPWRUPACK | CDBGPWRUPACK set


def test_wait_then_retry() -> None:
    assert (OPS[3]["apndp"], OPS[3]["ack"]) == ("AP", "WAIT") and "data" not in OPS[3]
    assert OPS[4]["ack"] == "OK" and OPS[4]["parity_ok"]
