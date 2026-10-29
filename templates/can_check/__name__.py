#!/usr/bin/env python3
"""@NAME@: check CAN traffic in a capture: CRC/ACK/stuffing, known IDs, DLC and send period
(saleae-box new can_check @NAME@). Use the logic side of the transceiver (RX pin).

    saleae-box python @NAME@.py CAPTURE [--spec spec.json]
    saleae-box python @NAME@.py --demo OUT.vcd
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
    fr = dec.can(capfmt.load(capture), spec["channel"], spec["bitrate"])
    want = {int(k, 16): v for k, v in spec["frames"].items()}
    bad, seen = [], {}
    for f in fr:
        if f["error"] or not f["crc_ok"] or not f["ack"]:
            bad.append(f"{f['start_time']:.6f}s id 0x{f['id']:X}: error={f['error']} crc_ok={f['crc_ok']} ack={f['ack']}")
            continue
        w = want.get(f["id"])
        if w is None:
            if spec.get("unknown_ids") == "fail":
                bad.append(f"unknown id 0x{f['id']:X}")
            continue
        if f["dlc"] != w["dlc"] or f["extended"] != w.get("extended", False):
            bad.append(f"id 0x{f['id']:X}: dlc {f['dlc']} extended {f['extended']}")
        seen.setdefault(f["id"], []).append(f["start_time"])
    for i, w in want.items():
        ts = seen.get(i, [])
        if len(ts) < 2:
            bad.append(f"id 0x{i:X}: seen {len(ts)} time(s), need 2+ for the period")
            continue
        per = [b - a for a, b in zip(ts, ts[1:])]
        p = w["period_ms"] / 1000
        if any(abs(x - p) > p * spec["period_tol"] for x in per):
            bad.append(f"id 0x{i:X}: periods {min(per) * 1e3:.2f}-{max(per) * 1e3:.2f} ms, want {w['period_ms']}")
    return bad


def demo(path: Path, spec: dict, duration: float = 0.06) -> None:
    ch = spec["channel"]
    ev = []
    for k, w in spec["frames"].items():
        n = int(duration / (w["period_ms"] / 1000))
        ev += [(j * w["period_ms"] / 1000 + 1e-4 * len(ev), int(k, 16), w) for j in range(n)]
    b = ls.Builder({ch: 1})
    for t, ident, w in sorted(ev, key=lambda e: e[0]):
        if b.t < t:
            b.wait(t - b.t)
        ls.can(b, ch, spec["bitrate"], ident, bytes(range(w["dlc"])), extended=w.get("extended", False))
    capfmt.save(b.digital(), path)


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
