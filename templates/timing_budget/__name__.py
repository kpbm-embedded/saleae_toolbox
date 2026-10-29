#!/usr/bin/env python3
"""@NAME@: measure edge-to-edge latency between two channels and check it against a budget
(saleae-box new timing_budget @NAME@).

    saleae-box python @NAME@.py CAPTURE [--spec spec.json] [--json]
    saleae-box python @NAME@.py --demo OUT.csv [--outlier-s 3e-4]
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


def stats(capture: Path, spec: dict) -> dict:
    lat = dec.latency(capfmt.load(capture), spec["src"], spec["dst"], spec["src_edge"] == "rising", spec["dst_edge"] == "rising")
    s = sorted(lat)
    if not s:
        return {"n": 0}

    def pct(p: float) -> float:
        return s[min(len(s) - 1, int(p / 100 * len(s)))]
    return {"n": len(s), "min_s": s[0], "p50_s": pct(50), f"p{spec['percentile']}_s": pct(spec["percentile"]), "max_s": s[-1]}


def check(capture: Path, spec: dict) -> list[str]:
    st = stats(capture, spec)
    bad = []
    if st["n"] < spec["min_samples"]:
        return [f"only {st['n']} samples (< {spec['min_samples']})"]
    key = f"p{spec['percentile']}_s"
    if st[key] > spec["budget_s"]:
        bad.append(f"{key[:-2]} {st[key] * 1e6:.1f} us > budget {spec['budget_s'] * 1e6:.1f} us")
    if st["max_s"] > spec["hard_max_s"]:
        bad.append(f"max {st['max_s'] * 1e6:.1f} us > hard limit {spec['hard_max_s'] * 1e6:.1f} us")
    return bad


def demo(path: Path, spec: dict, outlier_s: float = 0.0, n: int = 100) -> None:
    b = ls.Builder({spec["src"]: 0, spec["dst"]: 0})
    for i in range(n):
        lat = outlier_s if (outlier_s and i == n // 2) else spec["budget_s"] * (0.3 + 0.4 * ((i * 37) % 100) / 100)
        b.set(spec["src"], 1); b.wait(lat); b.set(spec["dst"], 1)
        b.wait(spec["hard_max_s"] * 2); b.set(spec["src"], 0); b.set(spec["dst"], 0); b.wait(spec["hard_max_s"])
    capfmt.save(b.digital(), path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("capture", type=Path, nargs="?")
    ap.add_argument("--spec", type=Path, default=HERE / "spec.json")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--demo", type=Path)
    ap.add_argument("--outlier-s", type=float, default=0.0)
    a = ap.parse_args(argv)
    spec = json.loads(a.spec.read_text())
    if a.demo:
        demo(a.demo, spec, a.outlier_s)
        return 0
    if not a.capture:
        ap.error("CAPTURE or --demo needed")
    st = stats(a.capture, spec)
    print(json.dumps(st, indent=2) if a.json else st)
    bad = check(a.capture, spec)
    for b in bad:
        print("FAIL", b)
    print("PASS @NAME@" if not bad else "FAIL @NAME@")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
