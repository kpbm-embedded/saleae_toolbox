#!/usr/bin/env bash
# about: ESP32-C3 ROM boot log on U0TXD 115200 with two 100 ns glitches, Logic 2 CSV: glitch scan, decode errors, glitch filter, autobaud and exact boot text
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
build() { python gen.py "$OUT"; }
case "$act" in
  build) build ;;
  run) build; python -I "$BOXT_ROOT/tools/decoders.py" "$OUT/esp32c3_boot.csv" glitch --map CH=U0TXD --min-width 2e-6 ;;
  test) build; python -m pytest -q -p no:cacheprovider test_boot_uart.py && echo "PASS esp32c3_boot_uart" ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
