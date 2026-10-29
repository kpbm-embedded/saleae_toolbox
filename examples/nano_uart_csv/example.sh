#!/usr/bin/env bash
# about: Arduino Nano (ATmega328P) UART 115200: Logic 2 digital CSV + Async Serial table parsed and decoded (fixtures, no Logic 2 needed)
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
build() { python -I gen_fixture.py "$OUT/nano_uart_digital.csv"; }
case "$act" in
  build) build; echo "wrote $OUT/nano_uart_digital.csv" ;;
  run) build; python -I "$BOXT_ROOT/tools/saleae_export.py" "$OUT/nano_uart_digital.csv" --uart "Channel 0:115200" ;;
  test) build; python -m pytest -q -p no:cacheprovider test_parse.py && echo "PASS nano_uart_csv" ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
