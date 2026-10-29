# @NAME@

Logic 2 automation script from `saleae-box new capture_script @NAME@` (32_16_saleae), using
Saleae's open-source `logic2-automation` API (Apache-2.0) from the saleae-box pixi env.

    saleae-box logic2 --automation &            # Logic 2 (installed after you accepted its licence)
    saleae-box python @NAME@.py --plan          # print what would be captured (no Logic 2 needed)
    saleae-box python @NAME@.py --seconds 2 --config analyzers.json --key blackpill_spi1
    saleae-box parse @NAME@_out/table.csv

Exit 77 = no automation server (skip). Analyzer settings: see `examples/analyzer_configs/analyzers.json`.
