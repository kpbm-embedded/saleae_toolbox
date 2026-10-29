# @NAME@

Glitch scan from `saleae-box new glitch_scan @NAME@` (32_16_saleae): every channel, pulses shorter
than `--min-width`, JSON report with the Logic 2 glitch-filter entries to set (`GlitchFilterEntry`
for automation, or Device settings > Glitch filter in the UI).

    saleae-box python @NAME@.py my_export.csv --min-width 500e-9 --report glitches.json
    saleae-box python -m pytest -q -p no:cacheprovider .
