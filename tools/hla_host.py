#!/usr/bin/env python3
"""Run a Logic 2 High Level Analyzer (HLA) extension on the host, without Logic 2.

Logic 2 loads an HLA from a folder with extension.json + a Python file whose class derives from
saleae.analyzers.HighLevelAnalyzer. That module exists only inside Logic 2, so this file provides
a small stand-in (HighLevelAnalyzer, AnalyzerFrame, StringSetting, NumberSetting, ChoicesSetting)
with the documented behaviour: settings are class attributes, `decode(frame)` receives the input
analyzer's frames and returns None, one AnalyzerFrame or a list of them.

Input frames come from decoders.py and use Logic 2's built-in analyzer frame types:
  I2C: start, address{address: bytes, read, ack}, data{data: bytes, ack}, stop
  Async Serial: data{data: bytes, error}
  SPI: enable, result{mosi: bytes, miso: bytes}, disable
This is a test harness for HLA logic; it does not reproduce Logic 2's UI or timing types exactly
(times are floats in seconds here, SaleaeTime objects in Logic 2).

Usage: hla_host.py <extension dir> <capture> <i2c|uart|spi> --map ROLE=ch,... [--setting k=v] [--baud N]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


class AnalyzerFrame:
    def __init__(self, type: str, start_time: float, end_time: float, data: dict | None = None):  # noqa: A002
        self.type, self.start_time, self.end_time, self.data = type, start_time, end_time, data or {}

    def __repr__(self) -> str:
        return f"AnalyzerFrame({self.type!r}, {self.start_time:.9f}, {self.end_time:.9f}, {self.data!r})"


class _Setting:
    def __init__(self, default=None, **kw):
        self.default, self.kw = default, kw

    def convert(self, v):
        return v


class StringSetting(_Setting):
    def __init__(self, label: str = "", **kw):
        super().__init__(kw.pop("default", ""), label=label, **kw)


class NumberSetting(_Setting):
    def __init__(self, label: str = "", min_value=None, max_value=None, **kw):
        super().__init__(kw.pop("default", min_value if min_value is not None else 0), label=label)
        self.min_value, self.max_value = min_value, max_value

    def convert(self, v):
        v = float(v)
        if (self.min_value is not None and v < self.min_value) or (self.max_value is not None and v > self.max_value):
            raise ValueError(f"setting {v} outside [{self.min_value}, {self.max_value}]")
        return v


class ChoicesSetting(_Setting):
    def __init__(self, choices, label: str = "", **kw):
        super().__init__(kw.pop("default", choices[0]), label=label)
        self.choices = tuple(choices)

    def convert(self, v):
        if v not in self.choices:
            raise ValueError(f"setting {v!r} not in {self.choices}")
        return v


class HighLevelAnalyzer:
    result_types: dict = {}

    def decode(self, frame: AnalyzerFrame):  # pragma: no cover - overridden
        raise NotImplementedError


def install_stub() -> None:
    """Make `from saleae.analyzers import ...` resolve to this harness."""
    mod = types.ModuleType("saleae.analyzers")
    for name in ("HighLevelAnalyzer", "AnalyzerFrame", "StringSetting", "NumberSetting", "ChoicesSetting"):
        setattr(mod, name, globals()[name])
    sys.modules["saleae.analyzers"] = mod


def load_extension(ext_dir: Path, settings: dict[str, str] | None = None) -> HighLevelAnalyzer:
    install_stub()
    meta = json.loads((ext_dir / "extension.json").read_text())
    ent = next(iter(meta["extensions"].values()))
    if ent.get("type") != "HighLevelAnalyzer":
        raise ValueError(f"{ext_dir}: first extension is not a HighLevelAnalyzer")
    src = ext_dir / ent["entryPoint"].split(".")[0]
    src = src.with_suffix(".py")
    spec = importlib.util.spec_from_file_location(f"hla_{ext_dir.name}", src)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    cls = getattr(m, ent["entryPoint"].split(".")[-1])
    obj = cls.__new__(cls)
    settings = settings or {}
    for k in dir(cls):
        v = getattr(cls, k)
        if isinstance(v, _Setting):
            setattr(obj, k, v.convert(settings.get(k, v.default)))
    unknown = set(settings) - {k for k in dir(cls) if isinstance(getattr(cls, k), _Setting)}
    if unknown:
        raise ValueError(f"unknown settings {sorted(unknown)}")
    if "__init__" in cls.__dict__:
        cls.__init__(obj)
    return obj


def frames_i2c(raw: list[dict]) -> list[AnalyzerFrame]:
    out = []
    for f in raw:
        d = {}
        if f["type"] == "address":
            d = {"address": bytes([f["address"]]), "read": f["read"], "ack": f["ack"]}
        elif f["type"] == "data":
            d = {"data": bytes([f["data"]]), "ack": f["ack"]}
        out.append(AnalyzerFrame(f["type"], f["start_time"], f["end_time"], d))
    return out


def frames_uart(raw: list[dict]) -> list[AnalyzerFrame]:
    return [AnalyzerFrame("data", f["start_time"], f["end_time"], {"data": bytes([f["data"]]), "error": f["error"] or None})
            for f in raw]


def frames_spi(raw: list[dict]) -> list[AnalyzerFrame]:
    out = []
    for t in raw:
        out.append(AnalyzerFrame("enable", t["start_time"], t["start_time"]))
        for mo, mi in zip(t["mosi"], t["miso"]):
            out.append(AnalyzerFrame("result", t["start_time"], t["end_time"], {"mosi": bytes([mo]), "miso": bytes([mi])}))
        out.append(AnalyzerFrame("disable", t["end_time"], t["end_time"]))
    return out


def run(hla: HighLevelAnalyzer, frames: list[AnalyzerFrame]) -> list[AnalyzerFrame]:
    out: list[AnalyzerFrame] = []
    for f in frames:
        r = hla.decode(f)
        if r is None:
            continue
        out += r if isinstance(r, list) else [r]
    return out


def input_frames(capture: Path, proto: str, roles: dict[str, str], baud: int = 115200) -> list[AnalyzerFrame]:
    import capfmt
    import decoders as dec
    d = capfmt.load(capture)
    if proto == "i2c":
        return frames_i2c(dec.i2c(d, roles["SCL"], roles["SDA"]))
    if proto == "uart":
        return frames_uart(dec.uart(d, roles["RX"], baud))
    return frames_spi(dec.spi(d, roles["CLK"], roles["MOSI"], roles.get("MISO"), roles.get("CS")))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run a Logic 2 HLA extension on a capture, on the host.")
    ap.add_argument("ext", type=Path)
    ap.add_argument("capture", type=Path)
    ap.add_argument("proto", choices=["i2c", "uart", "spi"])
    ap.add_argument("--map", required=True)
    ap.add_argument("--setting", action="append", default=[], help="name=value (repeatable)")
    ap.add_argument("--baud", type=int, default=115200)
    a = ap.parse_args(argv)
    roles = dict(p.split("=", 1) for p in a.map.split(","))
    hla = load_extension(a.ext, dict(s.split("=", 1) for s in a.setting))
    for f in run(hla, input_frames(a.capture, a.proto, {k.upper(): v for k, v in roles.items()}, a.baud)):
        print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
