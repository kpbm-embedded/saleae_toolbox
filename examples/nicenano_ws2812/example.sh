#!/usr/bin/env bash
# about: nice!nano (nRF52840) WS2812 driven by PWM at 16 MHz ticks, as sigrok .sr: GRB pixel decode, T0H/T1H/reset compliance (pass and fail capture)
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
build() { python gen.py "$OUT"; }
case "$act" in
  build) build ;;
  run) build; python -I "$BOXT_ROOT/tools/decoders.py" "$OUT/ws2812_ok.sr" ws2812 --map DIN=P0_06 ;;
  test) build; python -m pytest -q -p no:cacheprovider test_ws2812.py && echo "PASS nicenano_ws2812" ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
