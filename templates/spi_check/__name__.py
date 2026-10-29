#!/usr/bin/env python3
"""@NAME@: check a capture against expected SPI transactions (saleae-box new spi_check @NAME@).

    saleae-box python @NAME@.py CAPTURE [--spec spec.json]     # PASS / FAIL lines, exit 1 on FAIL
    saleae-box python @NAME@.py --demo OUT.csv                 # write a generated capture that passes
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


def match(want: str, got: list[int]) -> bool:
    g = "".join(f"{x:02x}" for x in got)
    return len(want) == len(g) and all(w in ("x", c) for w, c in zip(want.lower(), g))


def check(capture: Path, spec: dict) -> list[str]:
    d = capfmt.load(capture)
    m = spec["map"]
    tx = dec.spi(d, m["CLK"], m["MOSI"], m.get("MISO"), m.get("CS"), spec["mode"])
    bad = []
    clk = dec.line(d, m["CLK"]).edges(rising=True)
    if len(clk) > 1:
        f = 1 / min(b - a for a, b in zip(clk, clk[1:]))
        if f > spec["max_clock_hz"] * 1.001:
            bad.append(f"clock {f:.0f} Hz > {spec['max_clock_hz']}")
    for i, e in enumerate(spec["expect"]):
        if i >= len(tx):
            bad.append(f"#{i} {e['what']}: missing")
            continue
        t = tx[i]
        if not match(e["mosi"], t["mosi"]) or not match(e["miso"], t["miso"]) or t["partial_bits"]:
            bad.append(f"#{i} {e['what']}: mosi {bytes(t['mosi']).hex()} miso {bytes(t['miso']).hex()} partial {t['partial_bits']}")
    return bad


def demo(path: Path, spec: dict) -> None:
    m = spec["map"]
    b = ls.Builder({m["CS"]: 1, m["CLK"]: spec["mode"] >> 1, m["MISO"]: 1, m["MOSI"]: 0})
    txns = [(bytes.fromhex(e["mosi"]), bytes.fromhex(e["miso"].replace("x", "f"))) for e in spec["expect"]]
    ls.spi(b, txns, spec["max_clock_hz"] / 2, spec["mode"], clk=m["CLK"], mosi=m["MOSI"], miso=m["MISO"], cs=m["CS"])
    capfmt.save(b.digital(), path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("capture", type=Path, nargs="?")
    ap.add_argument("--spec", type=Path, default=HERE / "spec.json")
    ap.add_argument("--demo", type=Path, help="write a generated capture that passes, then exit")
    a = ap.parse_args(argv)
    spec = json.loads(a.spec.read_text())
    if a.demo:
        demo(a.demo, spec)
        return 0
    if not a.capture:
        ap.error("CAPTURE or --demo needed")
    bad = check(a.capture, spec)
    for b in bad:
        print("FAIL", b)
    print("PASS @NAME@" if not bad else f"FAIL @NAME@: {len(bad)} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
