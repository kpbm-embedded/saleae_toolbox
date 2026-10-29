#!/usr/bin/env bash
# about: Pico 2 (RP2350) I2C1 to a BME280 decoded by a Logic 2 HLA extension (bme280_hla/) run in the host harness tools/hla_host.py: register names, chip id, raw temperature (no Logic 2)
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
build() { python gen.py "$OUT"; }
case "$act" in
  build) build ;;
  run) build; python -I "$BOXT_ROOT/tools/hla_host.py" bme280_hla "$OUT/pico2_i2c.csv" i2c --map SCL=GP7_SCL,SDA=GP6_SDA ;;
  test) build; python -m pytest -q -p no:cacheprovider test_hla.py && echo "PASS pico2_i2c_hla" ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
