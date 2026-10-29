# @NAME@

WS2812 check from `saleae-box new ws2812_check @NAME@` (32_16_saleae): bit timing (T0H/T1H, reset),
pixel count, expected colours (`spec.json`). Sample at 20 MHz or more.

    saleae-box python @NAME@.py my_capture.sr
    saleae-box python -m pytest -q -p no:cacheprovider .
