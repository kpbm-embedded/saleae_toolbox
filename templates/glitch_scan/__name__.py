#!/usr/bin/env python3
"""@NAME@: scan every channel of a capture for pulses shorter than --min-width, write a JSON report
and the matching Logic 2 glitch-filter settings (saleae-box new glitch_scan @NAME@).

    saleae-box python @NAME@.py CAPTURE [--min-width 1e-6] [--report out.json]   # exit 1 if any glitch
    saleae-box python @NAME@.py --demo OUT.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from saleae import automation

import capfmt
import decoders as dec
import logicsim as ls


def scan(capture: Path, min_width: float) -> dict:
    d = capfmt.load(capture)
    rep = {"min_width_s": min_width, "channels": {}}
    for i, name in enumerate(d.channels):
        g = dec.glitches(d, name, min_width)
        g = [x for x in g if x["time"] > 0]          # the segment from t=0 is not a pulse
        real = [w for lv in (0, 1) for t, w in dec.line(d, name).pulses(lv) if t > 0 and w >= min_width]
        rep["channels"][name] = {"index": i, "glitches": len(g), "first": g[:3], "shortest_real_s": min(real) if real else None}
    return rep


def filters(rep: dict) -> list:
    """GlitchFilterEntry for each channel with glitches: half the shortest real pulse, at least min_width."""
    out = []
    for c in rep["channels"].values():
        if c["glitches"]:
            w = max(rep["min_width_s"], (c["shortest_real_s"] or rep["min_width_s"] * 2) / 2)
            out.append(automation.GlitchFilterEntry(channel_index=c["index"], pulse_width_seconds=w))
    return out


def demo(path: Path, glitch: bool = True) -> None:
    b = ls.Builder({"Channel 0": 1, "Channel 1": 0})
    ls.uart(b, "Channel 0", 115200, b"scan me")
    ls.pwm(b, "Channel 1", 10e3, 0.5, 5)
    if glitch:
        ls.glitch(b, "Channel 1", 0.2e-3, 50e-9)
    capfmt.save(b.digital(), path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("capture", type=Path, nargs="?")
    ap.add_argument("--min-width", type=float, default=1e-6)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--demo", type=Path)
    a = ap.parse_args(argv)
    if a.demo:
        demo(a.demo)
        return 0
    if not a.capture:
        ap.error("CAPTURE or --demo needed")
    rep = scan(a.capture, a.min_width)
    rep["logic2_glitch_filters"] = [{"channel_index": f.channel_index, "pulse_width_seconds": f.pulse_width_seconds} for f in filters(rep)]
    txt = json.dumps(rep, indent=2)
    if a.report:
        a.report.write_text(txt + "\n")
    print(txt)
    n = sum(c["glitches"] for c in rep["channels"].values())
    print("PASS @NAME@: no glitches" if not n else f"FAIL @NAME@: {n} glitch(es)")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
