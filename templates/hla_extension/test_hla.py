"""Host test of the @NAME@ HLA (tools/hla_host.py stands in for Logic 2's saleae.analyzers)."""
from pathlib import Path

import capfmt
import hla_host
import logicsim as ls

HERE = Path(__file__).parent


def capture(tmp_path: Path, text: bytes) -> Path:
    b = ls.Builder({"TX": 1})
    ls.uart(b, "TX", 115200, text)
    p = tmp_path / "uart.csv"
    capfmt.write_csv(b.digital(), p)
    return p


def lines(cap: Path, **settings) -> list:
    hla = hla_host.load_extension(HERE, {"max_len": 64, **settings})
    return hla_host.run(hla, hla_host.input_frames(cap, "uart", {"RX": "TX"}))


def test_lines(tmp_path: Path) -> None:
    out = lines(capture(tmp_path, b"boot ok\r\nready\r\n"))
    assert [f.data["text"] for f in out] == ["boot ok", "ready"]


def test_overflow(tmp_path: Path) -> None:
    out = lines(capture(tmp_path, b"x" * 70 + b"\n"), max_len=64)
    assert out[0].type == "overflow"
