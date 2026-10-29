#!/usr/bin/env bash
# about: Pico (RP2040) I2C0 400 kHz to a BME280 as Logic 2 CSV: transactions, address-NAK scan, UM10204 Fast-mode tLOW/tHIGH compliance (pass and fail capture)
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
build() { python gen.py "$OUT"; }
case "$act" in
  build) build ;;
  run) build; python -I "$BOXT_ROOT/tools/decoders.py" "$OUT/pico_i2c_ok.csv" i2c --map SCL=GP5_SCL,SDA=GP4_SDA ;;
  test) build; python -m pytest -q -p no:cacheprovider test_i2c.py && echo "PASS pico_i2c_bme280_timing" ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
