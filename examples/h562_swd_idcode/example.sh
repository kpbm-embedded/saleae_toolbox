#!/usr/bin/env bash
# about: WeAct H562 SWD bring-up as Logic 2 CSV: line reset, JTAG-to-SWD, DPIDR read (Cortex-M33 DP v2), CTRL/STAT power-up, AP WAIT then retry; ACK and parity checks (generated, no probe)
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
build() { python gen.py "$OUT"; }
case "$act" in
  build) build ;;
  run) build; python -I "$BOXT_ROOT/tools/decoders.py" "$OUT/h562_swd.csv" swd --map SWCLK=SWCLK_PA14,SWDIO=SWDIO_PA13 ;;
  test) build; python -m pytest -q -p no:cacheprovider test_swd.py && echo "PASS h562_swd_idcode" ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
