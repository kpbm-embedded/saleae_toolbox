#!/usr/bin/env bash
# about: BlackPill F411 SPI1 + W25Q32 flash (JEDEC ID, status, read) as a Logic 2 binary export: SPI decode, clock rate and CS setup checks (generated capture)
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
build() { python gen.py "$OUT/export"; }
case "$act" in
  build) build ;;
  run) build; python -I "$BOXT_ROOT/tools/decoders.py" "$OUT/export" spi --map CS=Channel_0,CLK=Channel_1,MISO=Channel_2,MOSI=Channel_3 ;;
  test) build; python -m pytest -q -p no:cacheprovider test_spi_flash.py && echo "PASS blackpill_spi_flash" ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
