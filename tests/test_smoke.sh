#!/usr/bin/env bash
# Smoke test of saleae-box: the env's logic2-automation imports, the export parser decodes a
# generated capture, convert + decode round trip, every template is generated and its own test runs
# (Rust/Zig templates: skip when 32_17_embedded_rust / 32_24_microzig is not reachable), and Logic 2
# (if you installed it after accepting its licence) is extracted with resolvable libraries.
# Usage: tests/test_smoke.sh
# shellcheck disable=SC2015  # ok() always returns 0
set -uo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd -P)
Q="$HERE/saleae-box"
pass=0; failn=0; skipn=0
ok()   { printf 'ok    %s\n' "$*"; pass=$((pass+1)); }
bad()  { printf 'FAIL  %s\n' "$*"; failn=$((failn+1)); }
skip() { printf 'skip  %s\n' "$*"; skipn=$((skipn+1)); }
tmp=$(mktemp -d)
cleanup() { if command -v trash-put >/dev/null; then trash-put "$tmp"; fi; }   # own temp dir; never rm
trap cleanup EXIT
v=$("$Q" python -c 'import importlib.metadata as m; from saleae import automation; print(m.version("logic2-automation"))' 2>&1) \
  && ok "logic2-automation $v imports" || bad "logic2-automation: $v"
"$Q" python -I "$HERE/examples/nano_uart_csv/gen_fixture.py" "$tmp/nano.csv" >/dev/null 2>&1
out=$("$Q" parse "$tmp/nano.csv" --uart "Channel 0:115200" 2>&1)
grep -q "uart: hello nano" <<<"$out" && ok "parser decodes a generated UART capture" || bad "parser: $out"
if "$Q" new capture_script smoke_cap --dir "$tmp" >/dev/null 2>&1 && out=$("$Q" python "$tmp/smoke_cap/smoke_cap.py" --plan 2>&1) \
   && grep -q '"analyzer": "Async Serial"' <<<"$out"; then ok "template capture_script: generated, --plan runs"
else bad "template capture_script: $out"; fi
if "$Q" convert "$tmp/nano.csv" "$tmp/nano.sr" --samplerate 4000000 >/dev/null 2>&1 \
   && out=$("$Q" decode "$tmp/nano.sr" uart --map RX=Channel_0 --baud 115200 2>&1) && grep -q "hello nano" <<<"$out"; then
  ok "convert CSV -> sigrok .sr, decode uart"
else bad "convert/decode: $out"; fi
for k in hla_extension capture_test spi_check i2c_register_map can_check timing_budget pwm_check ws2812_check glitch_scan trigger_capture board_analyzers; do
  out=""
  if "$Q" new "$k" "smoke_$k" --dir "$tmp" >/dev/null 2>&1 && out=$("$Q" python -m pytest -q -p no:cacheprovider "$tmp/smoke_$k" 2>&1); then
    ok "template $k: generated, pytest $(tail -1 <<<"$out")"
  else bad "template $k: $(tail -3 <<<"$out")"; fi
done
for k in rust_decoder zig_decoder; do
  out=""; rc=1
  if "$Q" new "$k" "smoke_$k" --dir "$tmp" >/dev/null 2>&1; then out=$("$Q" run bash "$tmp/smoke_$k/test.sh" 2>&1); rc=$?; fi
  case "$rc" in
    0) ok "template $k: generated, host tests + cross build" ;;
    3) skip "template $k: toolchain ID not found ($(tail -1 <<<"$out"))" ;;
    *) bad "template $k: $(tail -3 <<<"$out")" ;;
  esac
done
if [[ -x "$HERE/install/logic2/root/AppRun" ]]; then
  b=$(find "$HERE/install/logic2/root" -maxdepth 1 -type f -perm -u+x -iname 'logic*' | head -1)
  if [[ -n "$b" ]] && ! ldd "$b" 2>/dev/null | grep 'not found' >/dev/null; then ok "Logic 2 extracted, $(basename "$b") libraries resolve"
  else bad "Logic 2 binary missing or libraries unresolved"; fi
else skip "Logic 2 not installed (proprietary: ./saleae-box install --accept-license)"; fi
if "$Q" automation-ping >/dev/null 2>&1; then ok "Logic 2 automation server is up"; else skip "Logic 2 automation server not running"; fi
echo "smoke: $pass ok, $failn failed, $skipn skipped"
[[ "$failn" -eq 0 ]]
