"""@NAME@: capture-to-pytest. `--cap-file F` tests a real export (CSV, VCD, .sr or a Logic 2 binary
export dir); without it a generated capture that matches expect.json is used."""
import json
from pathlib import Path

import pytest

import capfmt
import logicsim as ls

HERE = Path(__file__).parent


def pytest_addoption(parser):
    parser.addoption("--cap-file", default=None, help="capture to test (default: generated)")


@pytest.fixture(scope="session")
def expect() -> dict:
    return json.loads((HERE / "expect.json").read_text())


@pytest.fixture(scope="session")
def capture(request, expect, tmp_path_factory):
    f = request.config.getoption("--cap-file")
    if f:
        return capfmt.load(Path(f))
    b = ls.Builder({expect["channel"]: 1})
    ls.uart(b, expect["channel"], expect["baud"], expect["text"].encode())
    return b.digital()
