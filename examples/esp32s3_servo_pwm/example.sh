#!/usr/bin/env bash
# about: ESP32-S3 LEDC 50 Hz 14-bit servo PWM as a Logic 2 binary export: period, per-pulse width (1.0/1.5/2.0 ms) within one LEDC tick, capture-to-pytest assertions
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
build() { python gen.py "$OUT"; }
case "$act" in
  build) build ;;
  run) build; python -I "$BOXT_ROOT/tools/decoders.py" "$OUT/export" pwm --map OUT=Channel_0 ;;
  test) build; python -m pytest -q -p no:cacheprovider test_servo.py && echo "PASS esp32s3_servo_pwm" ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
