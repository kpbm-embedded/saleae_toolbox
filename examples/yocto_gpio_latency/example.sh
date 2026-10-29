#!/usr/bin/env bash
# about: Yocto SoC board (Raspberry Pi 4 / i.MX8, libgpiod) input-to-output GPIO latency: p50/p99/max against a 100 us budget, one outlier found; capture round-tripped through CSV, VCD, Logic 2 binary and sigrok .sr
# Usage (through ./saleae-box examples ...): example.sh build | run | test
set -euo pipefail
act=${1:-run}
OUT=${EX_OUT:?run through ./saleae-box examples}
build() { python gen.py "$OUT"; }
case "$act" in
  build) build ;;
  run) build; python -c 'import capfmt, decoders as d, sys; print(sorted(d.latency(capfmt.load(sys.argv[1]), "GPIO17_IN", "GPIO27_OUT"))[-5:])' "$OUT/gpio.csv" ;;
  test) build; python -m pytest -q -p no:cacheprovider test_latency.py && echo "PASS yocto_gpio_latency" ;;
  *) echo "usage: example.sh build|run|test" >&2; exit 2 ;;
esac
