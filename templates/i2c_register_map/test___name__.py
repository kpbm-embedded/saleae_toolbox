"""Tests for @NAME@.py on generated captures."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).parent
s = importlib.util.spec_from_file_location("chk", HERE / "@NAME@.py")
chk = importlib.util.module_from_spec(s)
s.loader.exec_module(chk)
RM = json.loads((HERE / "regmap.json").read_text())


def test_demo_passes(tmp_path: Path) -> None:
    chk.demo(tmp_path / "ok.csv", RM)
    assert chk.accesses(tmp_path / "ok.csv", RM)[1] == ("read", "id", "60")
    assert chk.check(tmp_path / "ok.csv", RM) == []


def test_short_tlow_fails(tmp_path: Path) -> None:
    chk.demo(tmp_path / "bad.csv", RM, t_low=1.0e-6)
    assert any("tLOW" in b for b in chk.check(tmp_path / "bad.csv", RM))
