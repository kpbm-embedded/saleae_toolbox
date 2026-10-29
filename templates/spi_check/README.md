# @NAME@

SPI transaction check from `saleae-box new spi_check @NAME@` (32_16_saleae). Put the expected
transactions in `spec.json` (hex, `x` = don't care), export the capture from Logic 2 (CSV, VCD,
binary dir) and run:

    saleae-box python @NAME@.py my_export_dir            # exit 1 on a mismatch
    saleae-box python -m pytest -q -p no:cacheprovider .  # self-test on generated captures
