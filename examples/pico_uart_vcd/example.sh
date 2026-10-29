#!/usr/bin/env bash
# about: Raspberry Pi Pico (RP2040) UART0 9600 + GP15 1 kHz as a Logic 2 VCD export: parsed, UART decoded, frequency checked
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
P="$BOXT_ROOT/tools/saleae_export.py"
build() { python -I gen_vcd.py "$OUT/pico.vcd"; }
case "$act" in
  build) build; echo "wrote $OUT/pico.vcd" ;;
  run) build; python -I "$P" "$OUT/pico.vcd" --uart GP0_UART0_TX:9600 ;;
  test)
    build
    out=$(python -I "$P" "$OUT/pico.vcd" --uart GP0_UART0_TX:9600 --json)
    echo "$out"
    grep -q '"uart": "pico\\n"' <<<"$out" || { echo "FAIL: UART decode"; exit 1; }
    grep -q '"min_pulse_s": 0.0005' <<<"$(grep -A5 '"GP15"' <<<"$out")" || { echo "FAIL: GP15 half period"; exit 1; }
    echo "PASS pico_uart_vcd" ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
