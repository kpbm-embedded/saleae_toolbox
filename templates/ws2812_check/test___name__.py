"""Tests for @NAME@.py on generated captures (sigrok .sr at 20 MHz)."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).parent
s = importlib.util.spec_from_file_location("chk", HERE / "@NAME@.py")
chk = importlib.util.module_from_spec(s)
s.loader.exec_module(chk)
SPEC = json.loads((HERE / "spec.json").read_text())


def test_demo_passes(tmp_path: Path) -> None:
    chk.demo(tmp_path / "ok.sr", SPEC)
    assert chk.check(tmp_path / "ok.sr", SPEC) == []


def test_slow_zero_bits_fail(tmp_path: Path) -> None:
    chk.demo(tmp_path / "bad.sr", SPEC, t0h=0.6e-6)
    assert any("outside T0H/T1H" in b for b in chk.check(tmp_path / "bad.sr", SPEC))
