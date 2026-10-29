"""Tests for @NAME@.py without Logic 2: API objects, plan, argument checks, skip without a server."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).parent
s = importlib.util.spec_from_file_location("chk", HERE / "@NAME@.py")
chk = importlib.util.module_from_spec(s)
s.loader.exec_module(chk)


def test_plan(capsys) -> None:
    assert chk.main(["--plan", "--edge", "pulse-low", "--channel", "2", "--glitch", "1e-7"]) == 0
    p = json.loads(capsys.readouterr().out)
    assert p["trigger"] == "pulse-low" and p["glitch_filters"] == 4


def test_objects() -> None:
    dev, cap = chk.configs(chk.parser().parse_args(["--edge", "falling", "--after", "0.5"]))
    assert cap.capture_mode.trigger_type == chk.automation.DigitalTriggerType.FALLING
    assert cap.capture_mode.after_trigger_seconds == 0.5 and dev.digital_sample_rate == 25_000_000


def test_bad_trigger_channel() -> None:
    assert chk.main(["--channels", "0", "1", "--channel", "5"]) == 2


def test_skip_without_server() -> None:
    assert chk.main(["--port", "59997"]) == 77              # live capture: Logic 2 + device only
