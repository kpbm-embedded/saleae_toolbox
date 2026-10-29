# @NAME@

Triggered Logic 2 automation capture from `saleae-box new trigger_capture @NAME@` (32_16_saleae):
digital trigger (rising, falling, pulse-high/low with minimum width), time kept after the trigger,
glitch filter, threshold, raw CSV + `.sal` export.

    saleae-box python @NAME@.py --plan
    saleae-box logic2 --automation &        # Logic 2 (after you accepted its licence) + analyser
    saleae-box python @NAME@.py --channel 2 --edge falling --after 0.5
    saleae-box python -m pytest -q -p no:cacheprovider .   # no Logic 2 needed; live part = exit 77

Not verified here: the live capture (needs Logic 2 and a Saleae analyser).
