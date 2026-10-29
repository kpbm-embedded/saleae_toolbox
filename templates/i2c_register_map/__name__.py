#!/usr/bin/env python3
"""@NAME@: I2C capture -> register access log with names; checks the expected sequence and the
UM10204 bus timing (saleae-box new i2c_register_map @NAME@).

    saleae-box python @NAME@.py CAPTURE [--map regmap.json]   # log + PASS/FAIL, exit 1 on FAIL
    saleae-box python @NAME@.py --demo OUT.csv                # generated capture that passes
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import capfmt
import decoders as dec
import logicsim as ls

HERE = Path(__file__).parent


def accesses(capture: Path, rm: dict) -> list[tuple[str, str, str]]:
    d = capfmt.load(capture)
    addr = int(rm["address"], 16)
    names = {int(k, 16): v for k, v in rm["registers"].items()}
    out, ptr = [], None
    for t in dec.i2c_transactions(dec.i2c(d, rm["map"]["SCL"], rm["map"]["SDA"])):
        if t["addr"] != addr or t["nak"] or not t["data"]:
            continue
        if t["read"]:
            out.append(("read", names.get(ptr, f"0x{ptr:02X}"), bytes(t["data"]).hex().upper()))
        else:
            ptr = t["data"][0]
            if len(t["data"]) > 1:
                out.append(("write", names.get(ptr, f"0x{ptr:02X}"), bytes(t["data"][1:]).hex().upper()))
    return out


def check(capture: Path, rm: dict) -> list[str]:
    bad = []
    got = accesses(capture, rm)
    want = [tuple(e) for e in rm["expect"]]
    if got[:len(want)] != want:
        bad.append(f"sequence {got} != {want}")
    f_max, t_low, t_high = dec.I2C_SPEC[rm["speed"]]
    t = dec.i2c_timing(capfmt.load(capture), rm["map"]["SCL"])
    if t["f_scl_hz"] and t["f_scl_hz"] > f_max * 1.001:
        bad.append(f"SCL {t['f_scl_hz']} Hz > {f_max:.0f}")
    if t["t_low_min_s"] < t_low or t["t_high_min_s"] < t_high:
        bad.append(f"tLOW {t['t_low_min_s']} / tHIGH {t['t_high_min_s']} below {rm['speed']} mode minimum")
    return bad


def demo(path: Path, rm: dict, t_low: float = 1.4e-6) -> None:
    m, addr = rm["map"], int(rm["address"], 16)
    regs = {v: int(k, 16) for k, v in rm["registers"].items()}
    b = ls.Builder({m["SCL"]: 1, m["SDA"]: 1})
    for op, reg, val in rm["expect"]:
        if op == "write":
            ls.i2c(b, [("w", addr, bytes([regs[reg]]) + bytes.fromhex(val))], scl=m["SCL"], sda=m["SDA"], t_low=t_low, t_high=1.1e-6)
        else:
            ls.i2c(b, [("w", addr, bytes([regs[reg]])), ("r", addr, bytes.fromhex(val))], scl=m["SCL"], sda=m["SDA"], t_low=t_low, t_high=1.1e-6)
    capfmt.save(b.digital(), path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("capture", type=Path, nargs="?")
    ap.add_argument("--map", type=Path, default=HERE / "regmap.json")
    ap.add_argument("--demo", type=Path)
    a = ap.parse_args(argv)
    rm = json.loads(a.map.read_text())
    if a.demo:
        demo(a.demo, rm)
        return 0
    if not a.capture:
        ap.error("CAPTURE or --demo needed")
    for acc in accesses(a.capture, rm):
        print(*acc)
    bad = check(a.capture, rm)
    for b in bad:
        print("FAIL", b)
    print("PASS @NAME@" if not bad else "FAIL @NAME@")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
