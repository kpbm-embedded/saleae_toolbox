#!/usr/bin/env bash
# about: WeAct H743 TIM1 encoder inputs as VCD: 4x quadrature count, direction reversals, an injected 80 ns glitch found and a matching GlitchFilterEntry built with saleae.automation
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
build() { python gen.py "$OUT"; }
case "$act" in
  build) build ;;
  run) build; python -I "$BOXT_ROOT/tools/decoders.py" "$OUT/h743_encoder.vcd" quadrature --map A=PE9_TIM1_CH1,B=PE11_TIM1_CH2 ;;
  test) build; python -m pytest -q -p no:cacheprovider test_quadrature.py && echo "PASS h743_quadrature" ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
