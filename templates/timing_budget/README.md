# @NAME@

Latency budget check from `saleae-box new timing_budget @NAME@` (32_16_saleae): for every `src` edge,
the time to the next `dst` edge; percentile vs `budget_s`, worst case vs `hard_max_s` (`spec.json`).
Typical: IRQ line to response GPIO on an MCU, or GPIO in to GPIO out through Linux on a Yocto board.

    saleae-box python @NAME@.py my_export.csv --json
    saleae-box python -m pytest -q -p no:cacheprovider .
