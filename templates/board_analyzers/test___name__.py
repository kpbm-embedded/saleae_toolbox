"""Tests for @NAME@.py: the shipped analyzers.json is valid; broken copies are caught."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).parent
s = importlib.util.spec_from_file_location("chk", HERE / "@NAME@.py")
chk = importlib.util.module_from_spec(s)
s.loader.exec_module(chk)
CFG = json.loads((HERE / "analyzers.json").read_text())


def test_valid() -> None:
    assert chk.problems(CFG) == []
    spi = next(v for k, v in CFG.items() if k.endswith("_spi"))
    assert "max_clock_hz" not in chk.logic2_settings(spi)


def test_errors_caught() -> None:
    bad = json.loads(json.dumps(CFG))
    i2c = next(k for k in bad if k.endswith("_i2c"))
    bad[i2c]["settings"]["SCL"] = 7
    bad[i2c]["sample_rate"] = 1_000_000
    p = chk.problems(bad)
    assert any("SCL=7 not enabled" in x for x in p) and any("sample rate" in x for x in p)
