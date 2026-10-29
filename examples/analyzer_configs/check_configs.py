"""Validate analyzers.json: known analyzer names, required settings, channel numbers within the
enabled channels, and that saleae.automation accepts the objects (no Logic 2 needed)."""
import argparse
import json
import sys
from pathlib import Path

from saleae import automation

REQUIRED = {
    "Async Serial": {"Input Channel", "Bit Rate (Bits/s)"},
    "SPI": {"MISO", "Clock", "Enable", "MOSI"},
    "I2C": {"SDA", "SCL"},
}
CHANNEL_KEYS = {"Input Channel", "MISO", "Clock", "Enable", "MOSI", "SDA", "SCL"}


def check(path: Path) -> int:
    """Validate every analyzer entry; return the number of valid entries (asserts on errors)."""
    cfg = json.loads(path.read_text())
    n = 0
    for key, c in cfg.items():
        if key.startswith("_"):
            continue
        name, st = c["analyzer"], c["settings"]
        missing = REQUIRED[name] - st.keys()
        assert not missing, f"{key}: missing {missing}"
        for k in CHANNEL_KEYS & st.keys():
            assert st[k] in c["channels"], f"{key}: {k}={st[k]} not in enabled channels {c['channels']}"
        if name == "Async Serial":
            assert c["sample_rate"] >= 4 * st["Bit Rate (Bits/s)"], f"{key}: sample rate too low"
        dev = automation.LogicDeviceConfiguration(enabled_digital_channels=c["channels"], digital_sample_rate=c["sample_rate"])
        automation.CaptureConfiguration(capture_mode=automation.TimedCaptureMode(duration_seconds=1.0))
        assert dev.enabled_digital_channels == c["channels"]
        print(f"ok  {key:18s} {name:12s} {c['board']}")
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate Logic 2 analyzer settings (analyzers.json).")
    ap.add_argument("config", type=Path, help="analyzers.json to check")
    a = ap.parse_args()
    try:
        n = check(a.config)
    except (AssertionError, KeyError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print(f"{n} analyzer configs valid")
    return 0 if n >= 4 else 1


if __name__ == "__main__":
    sys.exit(main())
