#!/usr/bin/env bash
# about: Logic 2 analyzer settings for all owned boards (Nano UART, BlackPill SPI1, Pico I2C0, ESP32-S3 UART0), validated against saleae.automation
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
case "$act" in
  build) cp analyzers.json "$OUT/"; echo "copied analyzers.json -> $OUT" ;;
  run|test) cp analyzers.json "$OUT/"; python check_configs.py analyzers.json && echo "PASS analyzer_configs" ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
