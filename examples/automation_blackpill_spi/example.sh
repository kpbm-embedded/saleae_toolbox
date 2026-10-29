#!/usr/bin/env bash
# about: logic2-automation capture of BlackPill STM32F411 SPI1 (template capture_script); runs only when Logic 2 --automation is up (SKIP otherwise)
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
CFG="$BOXT_ROOT/examples/analyzer_configs/analyzers.json"
build() {
  "$BOXT_ROOT/saleae-box" new capture_script blackpill_spi --dir "$OUT" --force >/dev/null
  python -m py_compile "$OUT/blackpill_spi/blackpill_spi.py"
  python "$OUT/blackpill_spi/blackpill_spi.py" --plan --config "$CFG" --key blackpill_spi1 >"$OUT/plan.json"
  grep -q '"analyzer": "SPI"' "$OUT/plan.json"
}
case "$act" in
  build) build; cat "$OUT/plan.json" ;;
  run|test)
    build
    rc=0; (cd "$OUT" && python blackpill_spi/blackpill_spi.py --config "$CFG" --key blackpill_spi1 --seconds 0.5 --out "$OUT/capture") || rc=$?
    case "$rc" in
      0) [[ -s "$OUT/capture/table.csv" ]] && python -I "$BOXT_ROOT/tools/saleae_export.py" "$OUT/capture/table.csv" && echo "PASS automation_blackpill_spi (live capture)" ;;
      77) echo "SKIP automation_blackpill_spi: Logic 2 automation server not running (plan + template checked)" ;;
      *) echo "FAIL automation_blackpill_spi (rc=$rc)"; exit 1 ;;
    esac ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
