#!/usr/bin/env python3
"""Capture file formats (stdlib only): read and write

  * Logic 2 digital raw-data CSV   (Time [s],Channel 0,...; one row per change)
  * VCD                            (1 ns timescale when written here)
  * Logic 2 binary export, digital (one digital_<n>.bin per channel; '<SALEAE>' header,
                                    version 0, type 0, initial state, begin/end time, transition times)
  * sigrok session .sr v2          (zip: version, metadata, logic-1-1 samples; written at a fixed
                                    sample rate, so edges move to the sample grid)

Usage (saleae-box convert ...): capfmt.py convert <in> <out> [--samplerate HZ]
  <in>/<out>: .csv, .vcd, .sr, or a directory (Logic 2 binary export)
"""
from __future__ import annotations

import argparse
import configparser
import io
import math
import re
import struct
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from saleae_export import Digital, read_digital_csv, read_vcd  # noqa: E402

BIN_MAGIC = b"<SALEAE>"


def end_time(d: Digital) -> float:
    return max((tr[-1][0] for tr in d.channels.values() if tr), default=0.0)


# ---------------------------------------------------------------- CSV / VCD
def write_csv(d: Digital, path: Path) -> None:
    names = list(d.channels)
    times = sorted({t for tr in d.channels.values() for t, _ in tr})
    idx = {n: 0 for n in names}
    lines = ["Time [s]," + ",".join(names)]
    for t in times:
        row = []
        for n in names:
            tr = d.channels[n]
            while idx[n] + 1 < len(tr) and tr[idx[n] + 1][0] <= t:
                idx[n] += 1
            row.append(str(tr[idx[n]][1]))
        lines.append(f"{t:.12f}," + ",".join(row))
    path.write_text("\n".join(lines) + "\n")


def write_vcd(d: Digital, path: Path) -> None:
    ids = {n: chr(33 + i) for i, n in enumerate(d.channels)}
    out = ["$timescale 1 ns $end", "$scope module top $end"]
    out += [f"$var wire 1 {ids[n]} {n.replace(' ', '_')} $end" for n in d.channels]
    out += ["$upscope $end", "$enddefinitions $end"]
    ev: dict[int, list[str]] = {}
    for n, tr in d.channels.items():
        for t, v in tr:
            ev.setdefault(round(t * 1e9), []).append(f"{v}{ids[n]}")
    for t in sorted(ev):
        out.append(f"#{t}")
        out += ev[t]
    path.write_text("\n".join(out) + "\n")


# ---------------------------------------------------------------- Logic 2 binary (digital, v0)
def write_bin_channel(tr: list[tuple[float, int]], path: Path, t_end: float) -> None:
    times = [t for t, _ in tr[1:]]
    hdr = BIN_MAGIC + struct.pack("<iiIddQ", 0, 0, tr[0][1], tr[0][0], t_end, len(times))
    path.write_bytes(hdr + struct.pack(f"<{len(times)}d", *times))


def read_bin_channel(path: Path) -> list[tuple[float, int]]:
    raw = path.read_bytes()
    if raw[:8] != BIN_MAGIC:
        raise ValueError(f"{path}: not a Logic 2 binary export (no <SALEAE> header)")
    version, typ, init, t0, _t1, n = struct.unpack_from("<iiIddQ", raw, 8)
    if version != 0 or typ != 0:
        raise ValueError(f"{path}: version {version} type {typ}: only digital v0 is read here")
    times = struct.unpack_from(f"<{n}d", raw, 8 + struct.calcsize("<iiIddQ"))
    tr, lv = [(t0, init)], init
    for t in times:
        lv ^= 1
        tr.append((round(t, 12), lv))
    return tr


def write_bin(d: Digital, outdir: Path) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    te = end_time(d)
    files = []
    for i, tr in enumerate(d.channels.values()):
        f = outdir / f"digital_{i}.bin"
        write_bin_channel(tr, f, te)
        files.append(f)
    return files


def read_bin_dir(path: Path) -> Digital:
    files = sorted(path.glob("digital_*.bin"), key=lambda p: int(re.findall(r"\d+", p.stem)[-1]))
    if not files:
        raise ValueError(f"{path}: no digital_*.bin files")
    return Digital({f"Channel {re.findall(r'[0-9]+', f.stem)[-1]}": read_bin_channel(f) for f in files})


# ---------------------------------------------------------------- sigrok .sr (session v2)
def fmt_rate(hz: int) -> str:
    for div, unit in ((1_000_000_000, "GHz"), (1_000_000, "MHz"), (1_000, "kHz")):
        if hz % div == 0:
            return f"{hz // div} {unit}"
    return f"{hz} Hz"


def parse_rate(s: str) -> int:
    m = re.match(r"\s*([\d.]+)\s*(GHz|MHz|kHz|Hz)?", s)
    if not m:
        raise ValueError(f"bad samplerate {s!r}")
    return int(float(m.group(1)) * {"GHz": 1e9, "MHz": 1e6, "kHz": 1e3, "Hz": 1, None: 1}[m.group(2)])


def write_sr(d: Digital, path: Path, samplerate: int) -> None:
    names = list(d.channels)
    unit = max(1, math.ceil(len(names) / 8))
    n = int(round(end_time(d) * samplerate)) + 1
    buf = bytearray(n * unit)
    for ci, name in enumerate(names):
        tr = d.channels[name]
        byte, mask = ci // 8, 1 << (ci % 8)
        for k, (t, v) in enumerate(tr):
            if not v:
                continue
            a = int(round(t * samplerate))
            b = int(round(tr[k + 1][0] * samplerate)) if k + 1 < len(tr) else n
            for s in range(a, b):
                buf[s * unit + byte] |= mask
    meta = ["[global]", "sigrok version=0.5.2", "", "[device 1]", "capturefile=logic-1",
            f"total probes={len(names)}", f"samplerate={fmt_rate(samplerate)}", "total analog=0"]
    meta += [f"probe{i + 1}={nm.replace(' ', '_')}" for i, nm in enumerate(names)]
    meta += [f"unitsize={unit}", ""]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("version", "2")
        z.writestr("metadata", "\n".join(meta))
        z.writestr("logic-1-1", bytes(buf))


def read_sr(path: Path) -> Digital:
    with zipfile.ZipFile(path) as z:
        if z.read("version").strip() != b"2":
            raise ValueError(f"{path}: only sigrok session version 2 is read here")
        cp = configparser.ConfigParser()
        cp.read_file(io.StringIO(z.read("metadata").decode()))
        dev = cp["device 1"]
        rate = parse_rate(dev["samplerate"])
        unit = int(dev.get("unitsize", "1"))
        nprobes = int(dev["total probes"])
        base = dev.get("capturefile", "logic-1")
        chunks = sorted((n for n in z.namelist() if n == base or n.startswith(base + "-")),
                        key=lambda s: int(s.rsplit("-", 1)[-1]) if s != base else 0)
        data = b"".join(z.read(c) for c in chunks)
    d = Digital()
    for p in range(nprobes):
        name = dev.get(f"probe{p + 1}", f"D{p}")
        byte, mask = p // 8, 1 << (p % 8)
        tr: list[tuple[float, int]] = []
        last = None
        for s in range(len(data) // unit):
            v = 1 if data[s * unit + byte] & mask else 0
            if v != last:
                tr.append((round(s / rate, 12), v))
                last = v
        d.channels[name] = tr
    return d


# ---------------------------------------------------------------- dispatch
def load(path: Path) -> Digital:
    path = Path(path)
    if path.is_dir():
        return read_bin_dir(path)
    suf = path.suffix.lower()
    if suf == ".sr":
        return read_sr(path)
    if suf == ".bin":
        return Digital({"Channel 0": read_bin_channel(path)})
    if suf == ".vcd":
        return read_vcd(path)
    return read_digital_csv(path)


def save(d: Digital, path: Path, samplerate: int = 0) -> None:
    path = Path(path)
    suf = path.suffix.lower()
    if suf == ".csv":
        write_csv(d, path)
    elif suf == ".vcd":
        write_vcd(d, path)
    elif suf == ".sr":
        if not samplerate:
            raise ValueError(".sr needs --samplerate")
        write_sr(d, path, samplerate)
    elif suf == "":
        write_bin(d, path)
    else:
        raise ValueError(f"unknown output format {path}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Convert logic captures between Logic 2 CSV, VCD, Logic 2 binary (dir) and sigrok .sr.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert", help="convert <in> <out>")
    c.add_argument("src", type=Path)
    c.add_argument("dst", type=Path)
    c.add_argument("--samplerate", type=int, default=0, help="for .sr output (Hz)")
    a = ap.parse_args(argv)
    try:
        d = load(a.src)
        save(d, a.dst, a.samplerate)
    except (ValueError, OSError, KeyError) as e:
        print(f"convert: {e}", file=sys.stderr)
        return 1
    print(f"{a.src} -> {a.dst}: {len(d.channels)} channels, {sum(len(t) - 1 for t in d.channels.values())} transitions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
