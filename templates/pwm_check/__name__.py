#!/usr/bin/env python3
"""@NAME@: PWM frequency / duty / jitter check (saleae-box new pwm_check @NAME@), e.g. a motor or
LED PWM from a timer: TIM on STM32, LEDC on ESP32, PWM slice on RP2040, PWM on nRF52.

    saleae-box python @NAME@.py CAPTURE [--spec spec.json]
    saleae-box python @NAME@.py --demo OUT.csv
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
    p = dec.pwm(capfmt.load(capture), spec["channel"])
    if p["cycles"] < 3:
        return [f"only {p['cycles']} PWM cycles"]
    bad = []
    if abs(p["freq_hz"] - spec["freq_hz"]) > spec["freq_hz"] * spec["freq_tol"]:
        bad.append(f"frequency {p['freq_hz']} Hz, want {spec['freq_hz']}")
    if abs(p["duty"] - spec["duty"]) > spec["duty_tol"]:
        bad.append(f"duty {p['duty']:.4f}, want {spec['duty']}")
    if p["jitter_pp_s"] > spec["jitter_max_s"]:
        bad.append(f"period jitter {p['jitter_pp_s'] * 1e9:.0f} ns > {spec['jitter_max_s'] * 1e9:.0f} ns")
    return bad


def demo(path: Path, spec: dict, duty: float | None = None, jitter: float = 0.0) -> None:
    ch, per = spec["channel"], 1 / spec["freq_hz"]
    hi = per * (duty if duty is not None else spec["duty"])
    b = ls.Builder({ch: 0})
    for i in range(50):                                      # every other period longer by `jitter`
        b.set(ch, 1); b.wait(hi); b.set(ch, 0); b.wait(per - hi + (jitter if i % 2 else 0.0))
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
