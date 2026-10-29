"""@NAME@: assertions on a capture (run: saleae-box python -m pytest -q . [--cap-file export.csv])."""
import decoders as dec


def test_baud(capture, expect) -> None:
    assert dec.estimate_baud(capture, expect["channel"]) == expect["baud"]


def test_text(capture, expect) -> None:
    fr = dec.uart(capture, expect["channel"], expect["baud"])
    assert not [f for f in fr if f["error"]]
    assert expect["text"].encode() in bytes(f["data"] for f in fr)


def test_no_glitches(capture, expect) -> None:
    assert dec.glitches(capture, expect["channel"], expect["max_glitch_s"]) == []
