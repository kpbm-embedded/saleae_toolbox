#!/usr/bin/env python3
"""@NAME@: Logic 2 automation capture (saleae-box new capture_script @NAME@).

Needs Logic 2 running with its automation server:  saleae-box logic2 --automation
(or Preferences > Automation > Enable). Logic 2 only READS the signals: nothing is written to
the target. Without a server this script exits 77 (= skip).

    saleae-box python @NAME@.py [--device-id ID] [--seconds 1.0] [--out DIR] [--config analyzers.json --key blackpill_spi1]
"""
import argparse
import json
import os
import socket
import sys
from pathlib import Path

from saleae import automation

DEFAULT = {"analyzer": "Async Serial", "channels": [0], "sample_rate": 4_000_000,
           "settings": {"Input Channel": 0, "Bit Rate (Bits/s)": 115200}}


def server_up(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", port)) == 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=int(os.environ.get("SALEAE_AUTOMATION_PORT", "10430")))
    ap.add_argument("--device-id", default=None, help="analyser serial (Logic 2 > Device); simulation devices work too")
    ap.add_argument("--seconds", type=float, default=1.0)
    ap.add_argument("--out", default="@NAME@_out")
    ap.add_argument("--config", default=None, help="analyzers.json (examples/analyzer_configs)")
    ap.add_argument("--key", default=None)
    ap.add_argument("--plan", action="store_true", help="print the capture plan and exit")
    a = ap.parse_args()
    cfg = DEFAULT if not a.config else json.loads(Path(a.config).read_text())[a.key]
    if a.plan:
        print(json.dumps({"port": a.port, "device": a.device_id, "seconds": a.seconds, **cfg}, indent=2))
        return 0
    if not server_up(a.port):
        print(f"SKIP @NAME@: no Logic 2 automation server on 127.0.0.1:{a.port} (saleae-box logic2 --automation)")
        return 77
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    with automation.Manager.connect(port=a.port) as mgr:
        dev = automation.LogicDeviceConfiguration(enabled_digital_channels=cfg["channels"], digital_sample_rate=cfg["sample_rate"])
        cap = automation.CaptureConfiguration(capture_mode=automation.TimedCaptureMode(duration_seconds=a.seconds))
        with mgr.start_capture(device_id=a.device_id, device_configuration=dev, capture_configuration=cap) as c:
            c.wait()
            h = c.add_analyzer(cfg["analyzer"], label="@NAME@", settings=cfg["settings"])
            c.export_data_table(filepath=str(out / "table.csv"), analyzers=[h])
            c.export_raw_data_csv(directory=str(out), digital_channels=cfg["channels"])
            c.save_capture(filepath=str(out / "@NAME@.sal"))
    print(f"@NAME@: wrote {out}/table.csv, digital.csv, @NAME@.sal (parse: saleae-box parse {out}/table.csv)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
