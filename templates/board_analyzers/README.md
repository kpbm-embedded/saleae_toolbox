# @NAME@

Analyzer settings for one board from `saleae-box new board_analyzers @NAME@` (32_16_saleae). Edit
`analyzers.json` (channels, pin labels, bit rates; examples: `examples/analyzer_configs/analyzers.json`
for Nano, BlackPill, Pico, ESP32-S3), then validate:

    saleae-box python @NAME@.py
    saleae-box python -m pytest -q -p no:cacheprovider .

Use it with `saleae-box new capture_script x` (`--config analyzers.json --key @NAME@_spi`).
