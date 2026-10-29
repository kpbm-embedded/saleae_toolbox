# @NAME@

I2C register log + sequence and timing check from `saleae-box new i2c_register_map @NAME@`
(32_16_saleae). `regmap.json`: device address, register names, expected accesses, bus speed
(`standard`, `fast`, `fast-plus`; UM10204 limits in `tools/decoders.py`).

    saleae-box python @NAME@.py my_export.csv
    saleae-box python -m pytest -q -p no:cacheprovider .
