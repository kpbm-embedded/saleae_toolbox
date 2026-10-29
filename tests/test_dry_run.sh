#!/usr/bin/env bash
# Every saleae-box command in --dry-run mode (no downloads or launches), the
# licensed-install logic on fixtures (tests/test_install_logic.sh), plus shellcheck of every script.
# Usage: tests/test_dry_run.sh
set -uo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd -P)
Q="$HERE/saleae-box"
pass=0; failn=0
check() { # name expected-regex cmd...
  local name=$1 re=$2; shift 2
  local out rc
  out=$(timeout 300 "$@" 2>&1); rc=$?
  if [[ "$rc" -eq 0 ]] && grep -qE -- "$re" <<<"$out"; then
    printf 'ok    %s\n' "$name"; pass=$((pass+1))
  else
    printf 'FAIL  %s (rc=%s)\n%s\n' "$name" "$rc" "$(tail -5 <<<"$out" | sed 's/^/      /')"; failn=$((failn+1))
  fi
}
check help        'usage: \./saleae-box'                   "$Q" help
check where       '^root '                                 "$Q" where
check bootstrap   'pixi .*install'                         "$Q" --dry-run bootstrap
check install-gate 'refused: Logic 2 licence not accepted' bash -c "SALEAE_BOX_GATE_ONLY=1 '$Q' install 2>&1; true"
check install     'curl -fL https://downloads2.saleae.com/logic2/Logic-2.4.48' "$Q" --dry-run install --accept-license
check licence     'support.saleae.com/faq/general-faq/license' "$Q" licence
check update      'pinned vs newest'                       "$Q" --dry-run update
check update-env  '\+ timeout .* update'                   "$Q" --dry-run update --env
check clean       'nothing to clean|dry run: re-run with --yes' "$Q" clean
check clean-all   'dry run: re-run with --yes'             "$Q" clean --all
check status      'logic2 +2\.4\.48'                       "$Q" status
check doctor      'doctor: [0-9]+ ok'                      bash -c "'$Q' doctor || true"
check shell       '\+ true'                                "$Q" --dry-run shell -- true
check run         '\+ python -V'                           "$Q" --dry-run run python -V
check test        'test_smoke\.sh'                         "$Q" --dry-run test
check new         '\+ copy .*templates/capture_script'     "$Q" --dry-run new capture_script demo --dir /nonexistent
check ex-list     'nano_uart_csv .*Nano'                   "$Q" examples list
check ex-run      'example\.sh run'                        "$Q" --dry-run examples run pico_uart_vcd
check ex-build    'example\.sh build'                      "$Q" --dry-run examples build
check ex-test     'example\.sh test'                       "$Q" --dry-run examples test
check native      'Logic2 @logic2'                         "$Q" --dry-run native
check relocate    'pixi env already matches|re-creating'   "$Q" --dry-run relocate
check pack        '\+ tar .*-cf .*saleae-box_'             "$Q" --dry-run pack
check list        '\+ lsusb'                               "$Q" --dry-run list
check logic2      '\+ Logic2 AppRun --automation'          "$Q" --dry-run logic2 --automation
check ping        '\+ probe 127.0.0.1:10430'               "$Q" --dry-run automation-ping
check parse       '\+ python tools/saleae_export.py x.csv'  "$Q" --dry-run parse x.csv
check python      '\+ python -V'                           "$Q" --dry-run python -V
check decode      '\+ python tools/decoders.py x.csv spi'  "$Q" --dry-run decode x.csv spi --map CLK=a,MOSI=b
check convert     '\+ python tools/capfmt.py convert a.csv b.sr' "$Q" --dry-run convert a.csv b.sr
check hla         '\+ python tools/hla_host.py ext c.csv i2c' "$Q" --dry-run hla ext c.csv i2c --map SCL=a,SDA=b
check decode-usage 'usage: ./saleae-box decode'            bash -c "'$Q' decode x 2>&1; [ \$? -eq 2 ]"
check new-hla     '\+ copy .*templates/hla_extension'     "$Q" --dry-run new hla_extension demo --dir /nonexistent
check install-logic 'install-logic: [0-9]+ ok, 0 failed'   bash "$HERE/tests/test_install_logic.sh"
if command -v shellcheck >/dev/null; then
  mapfile -t files < <(cd "$HERE" && { echo saleae-box; ls lib/*.bash tests/*.sh examples/*/example.sh templates/*/*.sh; })
  if out=$(cd "$HERE" && shellcheck -x "${files[@]}" 2>&1); then printf 'ok    shellcheck (%s files)\n' "${#files[@]}"; pass=$((pass+1))
  else printf 'FAIL  shellcheck\n%s\n' "$(head -30 <<<"$out")"; failn=$((failn+1)); fi
else printf 'skip  shellcheck (not installed)\n'; fi
echo "dry-run: $pass ok, $failn failed"
[[ "$failn" -eq 0 ]]
