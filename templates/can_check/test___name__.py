"""Tests for @NAME@.py on generated captures."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).parent
s = importlib.util.spec_from_file_location("chk", HERE / "@NAME@.py")
chk = importlib.util.module_from_spec(s)
s.loader.exec_module(chk)
SPEC = json.loads((HERE / "spec.json").read_text())


def test_demo_passes(tmp_path: Path) -> None:
    chk.demo(tmp_path / "ok.vcd", SPEC)
    assert chk.check(tmp_path / "ok.vcd", SPEC) == []


def test_wrong_period_and_unknown_id(tmp_path: Path) -> None:
    other = json.loads(json.dumps(SPEC))
    other["frames"]["0x123"]["period_ms"] = 15
    other["frames"]["0x456"] = {"dlc": 2, "period_ms": 30}
    chk.demo(tmp_path / "bad.vcd", other)
    bad = chk.check(tmp_path / "bad.vcd", SPEC)
    assert any("0x123: periods" in b for b in bad) and any("unknown id 0x456" in b for b in bad)
