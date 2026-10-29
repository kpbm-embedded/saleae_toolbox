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
    assert chk.check(tmp_path / "ok.csv", SPEC) == []


def test_wrong_duty_and_jitter(tmp_path: Path) -> None:
    chk.demo(tmp_path / "bad.csv", SPEC, duty=0.30, jitter=200e-9)
    bad = chk.check(tmp_path / "bad.csv", SPEC)
    assert any("duty" in b for b in bad) and any("jitter" in b for b in bad)
