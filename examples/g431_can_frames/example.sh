#!/usr/bin/env bash
# about: WeAct G431 FDCAN1 classic CAN 500 kbit/s (standard, extended, stuff-error frame) as VCD: frame decode, CRC15, ACK, bus load (generated capture)
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
build() { python gen.py "$OUT/g431_can.vcd"; }
case "$act" in
  build) build ;;
  run) build; python -I "$BOXT_ROOT/tools/decoders.py" "$OUT/g431_can.vcd" can --map RX=FDCAN1_RX --baud 500000 ;;
  test) build; python -m pytest -q -p no:cacheprovider test_can.py && echo "PASS g431_can_frames" ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
