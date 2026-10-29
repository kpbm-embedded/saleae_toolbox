#!/usr/bin/env bash
# @NAME@: zig test on the host + a freestanding Cortex-M33 (Pico 2 / WeAct H562) object, using the Zig
# pinned in 32_24_microzig (reached, not installed here).
# Run: saleae-box run bash test.sh [OUTDIR]      exit 3 = 32_24_microzig not found
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
zb=${SALEAE_ZIG_BOX:-${BOX_MICROZIG:+$BOX_MICROZIG/microzig-box}}
[[ -n "$zb" && -x "$zb" ]] || { echo "skip: 32_24_microzig not found (set BOX_MICROZIG)"; exit 3; }
out=${1:-$here/out}
mkdir -p "$out"
python "$here/gen_fixture.py" "$out/fixture.bin"
cp "$here/@NAME@.zig" "$out/decoder.zig"
cd "$out"
zb() { env -u BOXT_OUT -u BOXT_BUILD "$zb" "$@"; }
zb zig build-obj -target thumb-freestanding-eabihf -mcpu cortex_m33 -O ReleaseSmall --cache-dir "$out/.zig-cache" decoder.zig -femit-bin=decoder_m33.o
zb zig test --cache-dir "$out/.zig-cache" decoder.zig
echo "PASS @NAME@ (zig test + cortex_m33 object: $out/decoder_m33.o)"
