#!/usr/bin/env python3
"""@NAME@: validate a board's analyzers.json: required settings per analyzer, channels enabled, pin
labels for every channel, sample rate >= 4x the bit rate (UART) or 4x the max clock (SPI/I2C), and
that saleae.automation accepts the device configuration (saleae-box new board_analyzers @NAME@).

    saleae-box python @NAME@.py [analyzers.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from saleae import automation

REQUIRED = {"Async Serial": {"Input Channel", "Bit Rate (Bits/s)"}, "SPI": {"MISO", "Clock", "Enable", "MOSI"}, "I2C": {"SDA", "SCL"}}
CHANNEL_KEYS = {"Input Channel", "MISO", "Clock", "Enable", "MOSI", "SDA", "SCL"}


def problems(cfg: dict) -> list[str]:
    bad = []
    for key, c in cfg.items():
        if key.startswith("_"):
            continue
        st = c["settings"]
        if c["analyzer"] not in REQUIRED:
            bad.append(f"{key}: unknown analyzer {c['analyzer']}")
            continue
        miss = REQUIRED[c["analyzer"]] - st.keys()
        if miss:
            bad.append(f"{key}: missing {sorted(miss)}")
        for k in CHANNEL_KEYS & st.keys():
            if st[k] not in c["channels"]:
                bad.append(f"{key}: {k}={st[k]} not enabled")
        for ch in c["channels"]:
            if str(ch) not in c.get("pins", {}):
                bad.append(f"{key}: channel {ch} has no pin label")
        rate = st.get("Bit Rate (Bits/s)") or st.get("max_clock_hz") or 0
        if c["sample_rate"] < 4 * rate:
            bad.append(f"{key}: sample rate {c['sample_rate']} < 4 x {rate}")
        automation.LogicDeviceConfiguration(enabled_digital_channels=c["channels"], digital_sample_rate=c["sample_rate"])
    return bad


def logic2_settings(c: dict) -> dict:
    """The settings dict for Capture.add_analyzer (without this file's own keys)."""
    return {k: v for k, v in c["settings"].items() if k != "max_clock_hz"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config", type=Path, nargs="?", default=Path(__file__).parent / "analyzers.json")
    a = ap.parse_args(argv)
    bad = problems(json.loads(a.config.read_text()))
    for b in bad:
        print("FAIL", b)
    print("PASS @NAME@" if not bad else "FAIL @NAME@")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
