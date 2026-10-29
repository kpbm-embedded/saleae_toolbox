"""pytest: the BME280 HLA on the host harness, plus its settings validation."""
import os
from pathlib import Path

import pytest

import hla_host

HERE = Path(__file__).parent
CAP = Path(os.environ["EX_OUT"]) / "pico2_i2c.csv"


def frames(settings=None):
    hla = hla_host.load_extension(HERE / "bme280_hla", settings)
    return hla_host.run(hla, hla_host.input_frames(CAP, "i2c", {"SCL": "GP7_SCL", "SDA": "GP6_SDA"}))


def test_register_accesses() -> None:
    got = [(f.data["op"], f.data["reg"], f.data["value"]) for f in frames()]
    assert got == [("write", "reset", "B6"), ("read", "id", "60"), ("write", "ctrl_meas", "25"), ("read", "temp_msb", "7E ED 00")]


def test_raw_temperature() -> None:
    v = bytes.fromhex(frames()[-1].data["value"].replace(" ", ""))
    adc_t = (v[0] << 12) | (v[1] << 4) | (v[2] >> 4)
    assert adc_t == 519888                                    # the datasheet's example adc_T


def test_other_address_sees_nothing() -> None:
    assert frames({"address": "0x77"}) == []


def test_bad_setting_rejected() -> None:
    with pytest.raises(ValueError):
        frames({"address": "0x42"})
