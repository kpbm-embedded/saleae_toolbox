# @NAME@

Capture-to-pytest from `saleae-box new capture_test @NAME@` (32_16_saleae). `expect.json` says what
the capture must contain (UART text, baud, no glitches); the tests run on a generated capture unless
you pass a real export:

    saleae-box python -m pytest -q -p no:cacheprovider .
    saleae-box python -m pytest -q -p no:cacheprovider . --cap-file my_export.csv   # Logic 2 CSV/VCD/.sr/bin dir
