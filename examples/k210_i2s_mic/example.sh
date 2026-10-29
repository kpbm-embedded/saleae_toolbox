#!/usr/bin/env bash
# about: K210 (Sipeed Maix) I2S0 48 kHz 16-bit stereo as VCD: Philips I2S decode, 1 kHz tone frequency and level on the left channel, right channel silent (generated)
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
build() { python gen.py "$OUT"; }
case "$act" in
  build) build ;;
  run) build; python -I "$BOXT_ROOT/tools/decoders.py" "$OUT/k210_i2s.vcd" i2s --map SCK=I2S0_SCLK,WS=I2S0_WS,SD=I2S0_SD --bits 16 | head -8 ;;
  test) build; python -m pytest -q -p no:cacheprovider test_i2s.py && echo "PASS k210_i2s_mic" ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
