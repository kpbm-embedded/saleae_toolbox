"""Tests for @NAME@.py on generated captures."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).parent
s = importlib.util.spec_from_file_location("chk", HERE / "@NAME@.py")
chk = importlib.util.module_from_spec(s)
s.loader.exec_module(chk)


def test_glitch_found_and_filter(tmp_path: Path) -> None:
    chk.demo(tmp_path / "g.csv")
    rep = chk.scan(tmp_path / "g.csv", 1e-6)
    assert rep["channels"]["Channel 1"]["glitches"] == 1 and rep["channels"]["Channel 0"]["glitches"] == 0
    f = chk.filters(rep)
    assert len(f) == 1 and f[0].channel_index == 1 and 1e-6 <= f[0].pulse_width_seconds <= 25e-6


def test_clean_capture(tmp_path: Path) -> None:
    chk.demo(tmp_path / "c.csv", glitch=False)
    assert chk.main([str(tmp_path / "c.csv"), "--report", str(tmp_path / "r.json")]) == 0
    assert json.loads((tmp_path / "r.json").read_text())["logic2_glitch_filters"] == []
