"""Tests for @NAME@.py on generated captures (saleae-box python -m pytest -q .)."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).parent
spec_ = importlib.util.spec_from_file_location("chk", HERE / "@NAME@.py")
chk = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(chk)
SPEC = json.loads((HERE / "spec.json").read_text())


def test_demo_passes(tmp_path: Path) -> None:
    chk.demo(tmp_path / "ok.csv", SPEC)
    assert chk.check(tmp_path / "ok.csv", SPEC) == []


def test_wrong_reply_fails(tmp_path: Path) -> None:
    bad = json.loads(json.dumps(SPEC))
    bad["expect"][0]["miso"] = "ffc22016"                     # a different flash answers
    chk.demo(tmp_path / "bad.csv", bad)
    assert chk.check(tmp_path / "bad.csv", SPEC)
