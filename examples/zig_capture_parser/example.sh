#!/usr/bin/env bash
# about: Zig 0.17 (via 32_24_microzig) Logic 2 binary-export parser + SPI mode-0 decoder: zig test on a Pico SPI0 SD-card CMD0 capture, cross-built for Cortex-M0+ (exit 3 when 32_24 is missing)
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
ZB=${SALEAE_ZIG_BOX:-}
[[ -n "$ZB" && -x "$ZB" ]] || { echo "skip: 32_24_microzig not found (set BOX_MICROZIG)"; exit 3; }
zb() { env -u BOXT_OUT -u BOXT_BUILD "$ZB" "$@"; }
build() {
  python gen.py "$OUT"
  cp capparse.zig "$OUT/"
  (cd "$OUT" && zb zig build-obj -target thumb-freestanding-eabi -mcpu cortex_m0plus -O ReleaseSmall \
     --cache-dir "$OUT/.zig-cache" capparse.zig -femit-bin=capparse_m0plus.o)
  grep -q capparse_spi "$OUT/capparse_m0plus.o" || { echo "FAIL: exported symbol capparse_spi missing"; exit 1; }
  echo "built $OUT/capparse_m0plus.o ($(wc -c <"$OUT/capparse_m0plus.o") bytes, freestanding)"
}
case "$act" in
  build) build ;;
  run|test)
    build
    (cd "$OUT" && zb zig test --cache-dir "$OUT/.zig-cache" capparse.zig)
    [[ "$act" = test ]] && echo "PASS zig_capture_parser" ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
