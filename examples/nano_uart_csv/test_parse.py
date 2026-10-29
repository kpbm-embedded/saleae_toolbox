"""pytest: tools/saleae_export.py on the Arduino Nano UART fixtures."""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.environ["BOXT_ROOT"], "tools"))
import saleae_export as se  # noqa: E402

HERE = Path(__file__).parent
OUT = Path(os.environ["EX_OUT"])


def test_digital_csv_uart_decode() -> None:
    d = se.read_digital_csv(OUT / "nano_uart_digital.csv")
    assert "Channel 0" in d.channels
    assert se.uart_decode(d, "Channel 0", 115200) == b"hello nano\r\n"
    s = d.summary()["Channel 0"]
    assert abs(s["min_pulse_s"] - 1 / 115200) < 1e-6


def test_table_csv_bytes() -> None:
    rows = se.read_table_csv(HERE / "async_serial_table.csv")
    assert len(rows) == 12
    assert se.table_bytes(rows) == b"hello nano\r\n"


def test_cli_json(capsys) -> None:
    assert se.main([str(HERE / "async_serial_table.csv"), "--json"]) == 0
    assert '"bytes": "hello nano\\r\\n"' in capsys.readouterr().out
