#!/usr/bin/env python3
"""@NAME@: WS2812 timing and pixel check (saleae-box new ws2812_check @NAME@); T0H/T1H windows and
the 50 us reset come from the WS2812B datasheet (tools/decoders.py ws2812).

    saleae-box python @NAME@.py CAPTURE [--spec spec.json]
    saleae-box python @NAME@.py --demo OUT.sr
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


def check(capture: Path, spec: dict) -> list[str]:
    r = dec.ws2812(capfmt.load(capture), spec["channel"])
    bad = list(r["violations"][:5])
    if not r["frames"]:
        return bad + ["no frame found"]
    px = r["frames"][0]
    if len(px) != spec["pixels"]:
        bad.append(f"{len(px)} pixels, want {spec['pixels']}")
    for i, want in enumerate(spec.get("expect", [])):
        if i < len(px) and list(px[i]) != want:
            bad.append(f"pixel {i}: {px[i]}, want {tuple(want)}")
    return bad


def demo(path: Path, spec: dict, t0h: float = 0.35e-6) -> None:
    px = [tuple(p) for p in spec.get("expect", [])]
    px += [(0, 0, 0)] * (spec["pixels"] - len(px))
    b = ls.Builder({spec["channel"]: 0})
    ls.ws2812(b, spec["channel"], px, t0h=t0h)
    capfmt.save(b.digital(), path, samplerate=20_000_000)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("capture", type=Path, nargs="?")
    ap.add_argument("--spec", type=Path, default=HERE / "spec.json")
    ap.add_argument("--demo", type=Path)
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
    print("PASS @NAME@" if not bad else "FAIL @NAME@")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
