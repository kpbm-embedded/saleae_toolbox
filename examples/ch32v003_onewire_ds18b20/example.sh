#!/usr/bin/env bash
# about: CH32V003 1-Wire (PD6) to a DS18B20 as Logic 2 CSV: reset/presence, Read ROM, Convert T, Read Scratchpad, CRC8 and temperature; missing-sensor capture (generated)
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
build() { python gen.py "$OUT"; }
case "$act" in
  build) build ;;
  run) build; python -I "$BOXT_ROOT/tools/decoders.py" "$OUT/ds18b20.csv" onewire --map DQ=PD6 --json ;;
  test) build; python -m pytest -q -p no:cacheprovider test_onewire.py && echo "PASS ch32v003_onewire_ds18b20" ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
