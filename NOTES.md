# 32_16_saleae: notes

## 2026-10-25: created
- Box tool style (launcher `saleae-box`, `lib/boxtool.bash` copied unchanged, md5 b938d4f9...).
- Logic 2 2.4.48: URL from the redirect of `logic2api.saleae.com/download?os=linux&arch=x64`
  (HEAD/302 only; the AppImage was not downloaded). Licence page found via web search:
  support.saleae.com/faq/general-faq/license ("Saleae Software & SDK License Agreement").
- logic2-automation 1.0.11 from PyPI (Apache-2.0) in the pixi env. Mistake: the first
  `pixi install` was run directly with the launcher's PIXI_*/RATTLER_* variables (same cache dirs)
  instead of through the launcher; `saleae-box bootstrap` afterwards verified the env; ~/.cache unchanged.
- boxtool's `cmd_install` knows no `--accept-license`, so `install` is intercepted in
  lib/saleae.bash; without the flag it still bootstraps the open-source env, then exits 2.
- Parser fix: float noise in VCD times (0.49999.. ms) -> times rounded to 1e-12 s.
- Results: doctor 10 ok / 2 warnings (Logic 2 not installed, udev) / 0 failed; examples test 4/4
  (live capture SKIP inside); test_dry_run 30/30 (install-logic 12/12, shellcheck); smoke 3 ok, 2 skipped.

## 2026-10-25: script style pass (00_09_meta/04_agents/script_style.md)
- lib/boxtool.bash replaced by the cleaned shared version (md5 0c5ba426..., same as 32_06..32_10):
  usage errors exit 2, help has examples + environment sections.
- Tool lib: usage problems via `usage_error` (exit 2); tool-specific environment variables and
  examples added to the help text; `[ ]` -> `[[ ]]` in the lib, tests and example scripts
  (POSIX `sh` launcher and `#!/bin/sh` fixtures unchanged); dead code removed.
- The licence refusal now exits 2 instead of 3; Python scripts use argparse + main() + type hints + pathlib.

## 2026-10-25: readability pass 2 (script_style.md, scripts/README)
- lib/boxtool.bash (reference `00_09_meta/05_policy/templates/tool/lib/boxtool.bash`, synced to all 24 copies):
  `where`/`status`/`doctor`/`bootstrap`/`relocate` reject extra arguments (exit 2); colour only on a terminal
  and never with `NO_COLOR`; help lists `NO_COLOR`.
- examples/pico_uart_vcd: `| grep -q` under pipefail -> here-string.
- README: exit codes, `BOX_INTEGRATION` and `NO_COLOR` rows. Backups:
  `00_09_meta/02_logs/config_backups/2026_10_25_readability2_embedded_tools/`.

## 2026-10-29: examples, templates, decoders, git repo
- sigrok-cli / libsigrokdecode are not on conda-forge (pixi search), so the decoders are written here (stdlib):
  tools/decoders.py (UART, SPI 0-3, I2C + UM10204 timing, classic CAN with CRC15/stuffing, 1-Wire, WS2812,
  PWM, quadrature, I2S, SWD, glitches, deglitch, latency), tools/capfmt.py (Logic 2 CSV, VCD, Logic 2 binary
  digital v0, sigrok .sr v2), tools/logicsim.py (fixture waveforms), tools/hla_host.py (HLA host harness).
- New commands: decode, convert, hla. Rust/Zig reached in 32_17_embedded_rust / 32_24_microzig
  (BOX_EMBEDDED_RUST / BOX_MICROZIG, else the sibling folder); doctor reports them. BEAM: not added (host-side
  capture analysis; no AtomVM fit).
- 14 new examples (blackpill_spi_flash, g431_can_frames, pico_i2c_bme280_timing, nicenano_ws2812,
  ch32v003_onewire_ds18b20, h743_quadrature, esp32s3_servo_pwm, h562_swd_idcode, k210_i2s_mic, esp32c3_boot_uart,
  pico2_i2c_hla, yocto_gpio_latency, rust_capture_parser, zig_capture_parser) and 13 new templates (trigger_capture,
  board_analyzers, hla_extension, capture_test, spi_check, i2c_register_map, can_check, timing_budget, pwm_check,
  ws2812_check, glitch_scan, rust_decoder, zig_decoder). All captures are generated; no analyser attached.
- Problems found: Builder overwrote the idle level when the first edge was at t=0 (lead-in time added);
  glitches between sample points did not change a UART decode (example puts them on bit centres);
  Zig 0.17 has no `**` array repeat (`@splat`). boxtool counts example exit 3 as FAIL in `examples test`.
- .gitignore: `/cache` without slash (a cache symlink in a clone is ignored too), *.AppImage, build/log, .pixi,
  __pycache__, .zig-cache. Git repo created (main).
- Results: doctor 13 ok / 2 warn / 0 fail; examples 18/18 (live capture SKIP); smoke 17 ok / 2 skip;
  dry-run 35/35 (shellcheck); install logic 12/12.
