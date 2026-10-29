"""pytest: 1-Wire decode of the CH32V003 / DS18B20 capture."""
import os
from pathlib import Path

import capfmt
import decoders as dec
import logicsim as ls

OUT = Path(os.environ["EX_OUT"])
SEG = dec.onewire(capfmt.load(OUT / "ds18b20.csv"), "PD6")


def test_three_resets_with_presence() -> None:
    assert len(SEG) == 3 and all(s["presence"] for s in SEG)


def test_read_rom_crc() -> None:
    cmd, rom = SEG[0]["bytes"][0], bytes(SEG[0]["bytes"][1:])
    assert cmd == 0x33 and rom[0] == 0x28                    # DS18B20 family code
    assert ls.crc8_maxim(rom[:7]) == rom[7]


def test_temperature() -> None:
    assert SEG[1]["bytes"] == [0xCC, 0x44]
    sp = bytes(SEG[2]["bytes"][2:])
    assert ls.crc8_maxim(sp[:8]) == sp[8]
    raw = int.from_bytes(sp[:2], "little", signed=True)
    assert raw / 16 == 25.0625


def test_absent_sensor() -> None:
    seg = dec.onewire(capfmt.load(OUT / "ds18b20_absent.csv"), "PD6")
    assert len(seg) == 1 and not seg[0]["presence"]
