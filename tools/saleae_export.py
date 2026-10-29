#!/usr/bin/env python3
"""Parse Saleae Logic 2 exports without Logic 2.

Formats:
  * digital raw-data CSV  (File > Export Raw Data > CSV, or Capture.export_raw_data_csv):
        Time [s],Channel 0,Channel 1,...   one row per transition
  * analyzer data-table CSV (Capture.export_data_table / Export Table), e.g. Async Serial:
        name,type,start_time,duration,"data",...
  * VCD (File > Export Raw Data > VCD): $var wire 1 <id> <name> $end, #<time> then 0<id>/1<id>

Also a small software UART decoder over a digital channel (8N1, LSB first), so a raw capture
can be checked against what the Async Serial analyzer would show.

Usage: saleae_export.py <file> [--json] [--uart CH:BAUD]   (saleae-box parse ...)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Digital:
    """Transitions per channel: name -> list of (time_s, level)."""
    channels: dict[str, list[tuple[float, int]]] = field(default_factory=dict)

    def summary(self) -> dict:
        out = {}
        for name, tr in self.channels.items():
            highs = sum(1 for _, v in tr if v)
            out[name] = {
                "transitions": max(len(tr) - 1, 0),
                "first_s": tr[0][0] if tr else None,
                "last_s": round(tr[-1][0], 12) if tr else None,
                "rising": highs - (1 if tr and tr[0][1] else 0),
                "min_pulse_s": min_pulse(tr),
            }
        return out

    def level_at(self, name: str, t: float) -> int:
        level = 1
        for ts, v in self.channels[name]:
            if ts > t:
                break
            level = v
        return level


def min_pulse(tr: list[tuple[float, int]]) -> float | None:
    gaps = [b[0] - a[0] for a, b in zip(tr, tr[1:]) if b[0] > a[0]]
    return round(min(gaps), 12) if gaps else None


def read_digital_csv(path: Path) -> Digital:
    with path.open(newline="") as f:
        rows = list(csv.reader(f))
    if not rows or not rows[0] or not rows[0][0].lower().startswith("time"):
        raise ValueError(f"{path}: not a Logic 2 digital CSV (first column must be 'Time [s]')")
    names = [h.strip() for h in rows[0][1:]]
    d = Digital({n: [] for n in names})
    for r in rows[1:]:
        if not r:
            continue
        t = float(r[0])
        for n, v in zip(names, r[1:]):
            lv = int(v)
            tr = d.channels[n]
            if not tr or tr[-1][1] != lv:
                tr.append((t, lv))
    return d


def read_vcd(path: Path) -> Digital:
    ids: dict[str, str] = {}
    scale = 1e-9
    t = 0.0
    d = Digital()
    in_defs = True
    text = path.read_text()
    m = re.search(r"\$timescale\s+(\d+)\s*(s|ms|us|ns|ps|fs)\s+\$end", text)
    if m:
        scale = int(m.group(1)) * {"s": 1, "ms": 1e-3, "us": 1e-6, "ns": 1e-9, "ps": 1e-12, "fs": 1e-15}[m.group(2)]
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if in_defs:
            vm = re.match(r"\$var\s+\w+\s+1\s+(\S+)\s+(.+?)\s+\$end", line)
            if vm:
                ids[vm.group(1)] = vm.group(2)
                d.channels[vm.group(2)] = []
            if line.startswith("$enddefinitions"):
                in_defs = False
            continue
        if line.startswith("#"):
            t = int(line[1:]) * scale
        elif line[0] in "01" and line[1:] in ids:
            tr = d.channels[ids[line[1:]]]
            lv = int(line[0])
            if not tr or tr[-1][1] != lv:
                tr.append((t, lv))
    if not ids:
        raise ValueError(f"{path}: no 1-bit $var in VCD header")
    return d


def read_table_csv(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or "start_time" not in rows[0]:
        raise ValueError(f"{path}: not a Logic 2 analyzer data table (needs start_time)")
    return rows


def table_bytes(rows: list[dict]) -> bytes:
    """Async Serial / SPI / I2C tables: the 'data' (or 'mosi') column, hex '0x41' or a char."""
    out = bytearray()
    for r in rows:
        v = (r.get("data") or r.get("mosi") or "").strip()
        if not v:
            continue
        if v.lower().startswith("0x"):
            out.append(int(v, 16))
        elif len(v) == 1:
            out.append(ord(v))
        elif v in ("\\r", "\\n", "\\t"):
            out.append({"\\r": 13, "\\n": 10, "\\t": 9}[v])
    return bytes(out)


def uart_decode(d: Digital, ch: str, baud: int) -> bytes:
    """8N1 LSB-first, idle high: sample in the middle of each bit."""
    bit = 1.0 / baud
    tr = d.channels[ch]
    out = bytearray()
    t_end = tr[-1][0] if tr else 0
    i = 0
    while i < len(tr):
        t0, lv = tr[i]
        if lv == 0:  # falling edge = start bit
            if d.level_at(ch, t0 + bit * 0.5) == 0:
                b = 0
                for k in range(8):
                    if d.level_at(ch, t0 + bit * (1.5 + k)):
                        b |= 1 << k
                if d.level_at(ch, t0 + bit * 9.5) == 1 or t0 + bit * 9.5 > t_end:
                    out.append(b)
                t_next = t0 + bit * 9.5
                while i < len(tr) and tr[i][0] < t_next:
                    i += 1
                continue
        i += 1
    return bytes(out)


def load(path: Path) -> tuple[str, "Digital | list[dict]"]:
    head = path.read_text(errors="replace")[:512]
    if path.suffix.lower() == ".vcd" or head.lstrip().startswith("$"):
        return "digital", read_vcd(path)
    first = head.splitlines()[0].lower() if head else ""
    if first.startswith("time"):
        return "digital", read_digital_csv(path)
    return "table", read_table_csv(path)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Summarise a Saleae Logic 2 export (digital CSV, analyzer table CSV or VCD).")
    ap.add_argument("file", type=Path, help="export file: digital raw-data CSV, analyzer data-table CSV or .vcd")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    ap.add_argument("--uart", metavar="CH:BAUD", default=None,
                    help="decode 8N1 UART on digital channel CH at BAUD, e.g. 'Channel 0:115200'")
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    if not a.file.is_file():
        print(f"no such file: {a.file}", file=sys.stderr)
        return 1
    try:
        kind, data = load(a.file)
    except ValueError as e:
        print(f"cannot parse {a.file}: {e}", file=sys.stderr)
        return 1
    if kind == "digital":
        res: dict = {"file": str(a.file), "kind": "digital", "channels": data.summary()}
        if a.uart:
            ch, baud = a.uart.rsplit(":", 1)
            if ch not in data.channels:
                print(f"no channel '{ch}' (have: {', '.join(data.channels)})", file=sys.stderr)
                return 2
            res["uart"] = uart_decode(data, ch, int(baud)).decode("latin-1")
    else:
        res = {"file": str(a.file), "kind": "table", "rows": len(data),
               "analyzers": sorted({r.get("name", "") for r in data}),
               "bytes": table_bytes(data).decode("latin-1")}
    if a.json:
        print(json.dumps(res, indent=2))
    else:
        for k, v in res.items():
            print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
