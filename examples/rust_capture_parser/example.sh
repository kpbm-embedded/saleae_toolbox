#!/usr/bin/env bash
# about: Rust (via 32_17_embedded_rust) no_std Logic 2 binary-export parser + UART decoder: host unit tests on a BlackPill USART2 capture, cross-built for thumbv7em (exit 3 when 32_17 is missing)
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
RB=${SALEAE_RUST_BOX:-}
[[ -n "$RB" && -x "$RB" ]] || { echo "skip: 32_17_embedded_rust not found (set BOX_EMBEDDED_RUST)"; exit 3; }
rb() { env -u BOXT_OUT -u BOXT_BUILD "$RB" "$@"; }   # its own output root, not this ID's
build() {
  python gen.py "$OUT"
  cp capparse.rs "$OUT/"
  (cd "$OUT" && rb run rustc --edition 2021 --crate-type rlib --target thumbv7em-none-eabihf -O capparse.rs -o libcapparse_thumbv7em.rlib)
  echo "built $OUT/libcapparse_thumbv7em.rlib ($(wc -c <"$OUT/libcapparse_thumbv7em.rlib") bytes, no_std)"
}
case "$act" in
  build) build ;;
  run|test)
    build
    (cd "$OUT" && rb run rustc --edition 2021 --test capparse.rs -o capparse_test && ./capparse_test)
    [[ "$act" = test ]] && echo "PASS rust_capture_parser" ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
