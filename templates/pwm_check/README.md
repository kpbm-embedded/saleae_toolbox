# @NAME@

PWM check from `saleae-box new pwm_check @NAME@` (32_16_saleae): frequency, duty and period jitter
against `spec.json`.

    saleae-box python @NAME@.py my_export.csv
    saleae-box python -m pytest -q -p no:cacheprovider .
