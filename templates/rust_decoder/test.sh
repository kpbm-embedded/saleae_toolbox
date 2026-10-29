#!/usr/bin/env bash
# @NAME@: host unit tests + a thumbv7em-none-eabihf (Cortex-M4F/M7: BlackPill, WeAct G431/H743) no_std
# build, using the pinned Rust of 32_17_embedded_rust (reached, not installed here).
# Run: saleae-box run bash test.sh [OUTDIR]      exit 3 = 32_17_embedded_rust not found
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
rb=${SALEAE_RUST_BOX:-${BOX_EMBEDDED_RUST:+$BOX_EMBEDDED_RUST/rust-box}}
[[ -n "$rb" && -x "$rb" ]] || { echo "skip: 32_17_embedded_rust not found (set BOX_EMBEDDED_RUST)"; exit 3; }
out=${1:-$here/out}
mkdir -p "$out"
python "$here/gen_fixture.py" "$out/fixture_pwm.bin"
cp "$here/@NAME@.rs" "$out/lib.rs"
cd "$out"
rb() { env -u BOXT_OUT -u BOXT_BUILD "$rb" "$@"; }
rb run rustc --edition 2021 --crate-name pwm_measure --crate-type rlib --target thumbv7em-none-eabihf -O lib.rs -o libpwm_measure.rlib
rb run rustc --edition 2021 --crate-name pwm_measure --test lib.rs -o pwm_measure_test
./pwm_measure_test
echo "PASS @NAME@ (host tests + thumbv7em no_std build: $out/libpwm_measure.rlib)"
