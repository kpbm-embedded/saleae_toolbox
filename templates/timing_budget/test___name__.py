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
    chk.demo(tmp_path / "ok.csv", SPEC)
    st = chk.stats(tmp_path / "ok.csv", SPEC)
    assert st["n"] == 100 and st["max_s"] <= SPEC["budget_s"]
    assert chk.check(tmp_path / "ok.csv", SPEC) == []


def test_outlier_breaks_hard_limit(tmp_path: Path) -> None:
    chk.demo(tmp_path / "bad.csv", SPEC, outlier_s=SPEC["hard_max_s"] * 1.5)
    assert any("hard limit" in b for b in chk.check(tmp_path / "bad.csv", SPEC))
