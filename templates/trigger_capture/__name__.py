#!/usr/bin/env python3
"""@NAME@: Logic 2 automation capture that waits for a digital trigger (saleae-box new trigger_capture @NAME@).

Example: catch a rare event, e.g. a reset pulse on NRST or a fault GPIO going high, keep
--after seconds after it, glitch filter on noisy inputs, export raw CSV + .sal.
Needs Logic 2 with the automation server (saleae-box logic2 --automation); without one: exit 77 (skip).

    saleae-box python @NAME@.py --plan                      # build the API objects, print the plan
    saleae-box python @NAME@.py --channel 2 --edge falling --after 0.5 --out cap
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path

from saleae import automation

EDGES = {"rising": automation.DigitalTriggerType.RISING, "falling": automation.DigitalTriggerType.FALLING,
         "pulse-high": automation.DigitalTriggerType.PULSE_HIGH, "pulse-low": automation.DigitalTriggerType.PULSE_LOW}


def configs(a: argparse.Namespace):
    dev = automation.LogicDeviceConfiguration(
        enabled_digital_channels=a.channels, digital_sample_rate=a.rate, digital_threshold_volts=a.threshold,
        glitch_filters=[automation.GlitchFilterEntry(channel_index=c, pulse_width_seconds=a.glitch) for c in a.channels] if a.glitch else [])
    mode = automation.DigitalTriggerCaptureMode(
        trigger_type=EDGES[a.edge], trigger_channel_index=a.channel, after_trigger_seconds=a.after,
        min_pulse_width_seconds=a.min_pulse if a.edge.startswith("pulse") else None,
        trim_data_seconds=a.trim)
    return dev, automation.CaptureConfiguration(capture_mode=mode, buffer_size_megabytes=a.buffer_mb)


def server_up(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", port)) == 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=int(os.environ.get("SALEAE_AUTOMATION_PORT", "10430")))
    ap.add_argument("--device-id", default=None)
    ap.add_argument("--channels", type=int, nargs="+", default=[0, 1, 2, 3])
    ap.add_argument("--channel", type=int, default=0, help="trigger channel")
    ap.add_argument("--edge", choices=sorted(EDGES), default="rising")
    ap.add_argument("--min-pulse", type=float, default=1e-6, help="pulse triggers: minimum width")
    ap.add_argument("--after", type=float, default=0.1, help="seconds kept after the trigger")
    ap.add_argument("--trim", type=float, default=1.0, help="seconds kept in total")
    ap.add_argument("--rate", type=int, default=25_000_000)
    ap.add_argument("--threshold", type=float, default=None, help="volts (Logic Pro: 1.2/1.8/3.3)")
    ap.add_argument("--glitch", type=float, default=0.0, help="glitch filter width (s) on every channel")
    ap.add_argument("--buffer-mb", type=int, default=512)
    ap.add_argument("--out", default="@NAME@_out")
    ap.add_argument("--plan", action="store_true")
    return ap


def main(argv: list[str] | None = None) -> int:
    a = parser().parse_args(argv)
    if a.channel not in a.channels:
        print(f"trigger channel {a.channel} is not enabled ({a.channels})", file=sys.stderr)
        return 2
    dev, cap = configs(a)
    if a.plan:
        print(json.dumps({"port": a.port, "channels": a.channels, "rate": a.rate, "trigger": a.edge,
                          "trigger_channel": a.channel, "after_s": a.after, "trim_s": a.trim,
                          "glitch_filters": len(dev.glitch_filters)}, indent=2))
        return 0
    if not server_up(a.port):
        print(f"SKIP @NAME@: no Logic 2 automation server on 127.0.0.1:{a.port} (saleae-box logic2 --automation)")
        return 77
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    with automation.Manager.connect(port=a.port) as mgr:
        with mgr.start_capture(device_id=a.device_id, device_configuration=dev, capture_configuration=cap) as c:
            c.wait()
            c.export_raw_data_csv(directory=str(out), digital_channels=a.channels)
            c.save_capture(filepath=str(out / "@NAME@.sal"))
    print(f"@NAME@: wrote {out}/digital.csv and @NAME@.sal (check: saleae-box decode {out}/digital.csv glitch --map CH=Channel_0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
