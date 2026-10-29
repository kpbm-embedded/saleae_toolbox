# 32_16_saleae - Saleae Logic 2 and logic2-automation

Saleae Logic 2 (proprietary AppImage, extracted so no FUSE is needed) and Saleae's open-source logic2-automation
Python API (gRPC client, Apache-2.0) in a pixi env, plus an export parser (Logic 2 digital CSV, analyzer tables, VCD;
software UART decoder), stdlib protocol decoders (UART, SPI, I2C, CAN, 1-Wire, WS2812, PWM, quadrature, I2S, SWD,
glitches, latency), a converter between Logic 2 CSV, VCD, Logic 2 binary export and sigrok `.sr`, a host harness
for Logic 2 High Level Analyzers, analyzer setting templates for your boards and automation script templates. Use it
to capture and decode logic-analyzer traces on the Nano, Pico/Pico 2, BlackPill, WeAct G431/H562/H743, nice!nano,
ESP32-S3/C3, CH32V003, K210 and Yocto SoC boards, and to script captures. Everything except the live capture works
without Logic 2 and without an analyser.

**Logic 2 is proprietary.** It is downloaded only when you read the licence and run
`./saleae-box install --accept-license`. `bootstrap` installs only the open-source part.

Status: **needs user action** (licence not accepted, Logic 2 not installed; open-source part ready; doctor 13 ok /
2 warn, examples 18/18 with the live capture SKIP, 14 templates, smoke 17 ok / 2 skip, dry-run 35/35, 2026-10-29).
Launcher: `./saleae-box`.

## What's included

| Component | Version | Notes |
|---|---|---|
| Saleae Logic 2 | 2.4.48 | Linux x64 AppImage, 212.7 MB (2026-10-07); not installed until you accept; proprietary |
| logic2-automation | 1.0.11 | PyPI, Apache-2.0; wheel sha256 pinned in `pixi.lock` |
| Python, grpcio, protobuf, pytest | 3.12, 1.x | conda-forge via `pixi.lock` |
| `tools/saleae_export.py` | this ID | export parser + UART decoder, stdlib only |
| `tools/decoders.py`, `capfmt.py`, `logicsim.py`, `hla_host.py` | this ID | protocol decoders, file formats, signal generator, HLA host harness; stdlib only |
| Rust 1.99.1, Zig 0.17.0 | other IDs | reached in `32_17_embedded_rust` / `32_24_microzig` (`BOX_EMBEDDED_RUST`, `BOX_MICROZIG`, else the sibling folder); not installed here |
| pixi | 0.81.0 | sha256 pinned in the launcher |

Logic 2 is fetched from `https://logic2api.saleae.com/download?os=linux&arch=x64`, which redirects to
`https://downloads2.saleae.com/logic2/Logic-2.4.48-linux-x64.AppImage`. Licence: Saleae Software & SDK License
Agreement (<https://support.saleae.com/faq/general-faq/license>, also inside the AppImage) and
<https://www.saleae.com/policies/terms-of-service>; it may not be used with non-Saleae (clone) hardware. Saleae
publishes no checksum, so `install` records the sha256 on the first download in `config/pins.local.tsv` (TOFU) and
aborts on any later mismatch (`.part` kept). You may pin a `sha256:` by hand in the digest column of `config/licensed.tsv`.

## Quick start

```sh
cd "$BOX_SALEAE"                          # or: cd $BOX/30_39_tools/32_embedded/32_16_saleae
./saleae-box bootstrap && ./saleae-box doctor     # open-source part: env + automation API (no Logic 2)
./saleae-box parse capture.csv --uart "Channel 0:115200"   # decode an export, no Logic 2 needed
./saleae-box licence                      # read the licence URL; then (YOU accept):
./saleae-box install --accept-license     # downloads, records sha256, extracts Logic 2
./saleae-box logic2 --automation          # Logic 2 with the automation server on 127.0.0.1:10430
```

With the Box shell set up once (`box shell install --apply`), the `saleae-box` shim works from any folder,
and `box test|doctor|status saleae` run this launcher (`box clean saleae` is a dry run until `--apply`).
Standalone (no Box, or `BOX_INTEGRATION=0`), `./saleae-box` keeps its output in this folder.

## Commands

Global option: `--dry-run` / `-n` prints what a command would do. Exit codes: 0 ok, 1 failure, 2 usage error (unknown command or option, or arguments given to `where`, `status`, `doctor`, `bootstrap` or `relocate`), 3 not applicable. `help` ends with this tool's own examples and variables (`tool examples`, `tool environment`).

| Command | What it does | Example |
|---|---|---|
| `install [--no-demos]` | bootstraps, then refuses Logic 2 (exit 2) and prints the licence URL | `./saleae-box install` |
| `install --accept-license` | YOU accept Saleae's licence; records who/when in `config/local-licence.txt`, downloads the pinned AppImage, TOFU sha256, extracts to `install/logic2-2.4.48/` | `./saleae-box install --accept-license` |
| `licence` | the licence URL and what has been accepted on this machine | `./saleae-box licence` |
| `bootstrap` | pinned pixi + env (open-source part only; never Logic 2) | `./saleae-box bootstrap` |
| `update [--check\|--env]` | `--check` (default): pins vs newest upstream; `--env`: re-solve the pixi env (rewrites `pixi.lock`) | `./saleae-box update --check` |
| `clean [--all] [--yes]` | move build/log output (`--all`: + install/, .pixi, native/, downloads) to the Trash; dry run unless `--yes` | `./saleae-box --dry-run clean --all` |
| `status`, `where`, `doctor` | versions and sizes, paths, health checks (exit 1 on failure) | `./saleae-box doctor` |
| `shell [-- cmd ...]` | bash (or a command) with the tools on PATH | `./saleae-box shell` |
| `run <cmd> [args]` | one command inside the environment | `./saleae-box run python --version` |
| `list` | read-only: Saleae analysers on USB (`lsusb 21a9:*`) | `./saleae-box list` |
| `logic2 [args]` | start Logic 2 (extracted AppImage); `--automation` starts the automation server | `./saleae-box logic2 --automation` |
| `automation-ping [port]` | is Logic 2's automation server up? (127.0.0.1:10430) | `./saleae-box automation-ping` |
| `parse <file.csv\|.vcd>` | summarise a Logic 2 export (`tools/saleae_export.py`); `--uart "Channel 0:115200"` decodes UART | `./saleae-box parse capture.csv --uart "Channel 0:115200"` |
| `python [args]` | the env's Python with `saleae.automation` | `./saleae-box python myscript.py` |
| `decode <cap> <proto> --map ROLE=ch,...` | decode a capture (`.csv`, `.vcd`, `.sr`, Logic 2 binary export dir): `uart spi i2c can onewire ws2812 pwm quadrature i2s swd glitch`; `_` in a channel name = space | `./saleae-box decode cap.csv i2c --map SCL=Channel_1,SDA=Channel_0 --json` |
| `convert <in> <out> [--samplerate HZ]` | between Logic 2 CSV, VCD, Logic 2 binary (dir) and sigrok `.sr` (needs `--samplerate`) | `./saleae-box convert cap.csv cap.sr --samplerate 10000000` |
| `hla <ext dir> <cap> <i2c\|uart\|spi> --map ...` | run a Logic 2 HLA extension on a capture on the host | `./saleae-box hla my_hla cap.csv uart --map RX=Channel_0` |
| `new <kind> <name> [--dir D] [--force]` | project from `templates/` (14 kinds, table below) | `./saleae-box new spi_check my_flash` |
| `test [--all]` | `tests/test_smoke.sh`; `--all` adds the dry-run test and examples test | `./saleae-box test` |
| `examples list \| run <ex> [args] \| build [ex...] \| test [ex...]` | list, run, build or test the examples | `./saleae-box examples test` |
| `native [--print]` | write `native/{native.zsh,native.bash,bin/}` | `./saleae-box native` |
| `relocate` | after moving the folder: re-create the pixi env, rewrite `native/` | `./saleae-box relocate` |
| `pack [--with-cache] [--out F]` | tarball of this folder (minus envs/build) for another machine | `./saleae-box pack --out /tmp/p.tgz` |
| `help`, `-h`, `--help` | the command list | `./saleae-box help` |

## Examples and templates

`./saleae-box examples list`, then `examples test`. No analyser is attached: every example generates its capture
(`tools/logicsim.py`) in a real export format and decodes it; only the live capture of `automation_blackpill_spi`
needs Logic 2 (SKIP otherwise). The Rust/Zig examples exit 3 (skip) when the toolchain ID is not reachable.

| Example | Board | What it shows |
|---|---|---|
| `nano_uart_csv` | Arduino Nano | generated Logic 2 digital CSV of `Serial.print("hello nano")` at 115200 + an Async Serial table fixture; parser + UART decoder (pytest, 3 tests) |
| `pico_uart_vcd` | Raspberry Pi Pico | VCD export (UART0 9600 + GP15 1 kHz): channels, half period 0.5 ms, UART decode |
| `analyzer_configs` | Nano, BlackPill F411, Pico, ESP32-S3 | `analyzers.json`: Async Serial / SPI1 / I2C0 / UART0 settings for `Capture.add_analyzer`, validated against the API objects |
| `automation_blackpill_spi` | BlackPill SPI1 | `capture_script` template: `--plan` always; live timed capture + SPI analyzer + CSV/`.sal` export only when Logic 2 `--automation` runs (SKIP otherwise) |
| `blackpill_spi_flash` | BlackPill F411 SPI1 + W25Q32 | Logic 2 binary export: JEDEC ID, status, read data; clock rate and CS setup checks |
| `g431_can_frames` | WeAct G431 FDCAN1 | VCD, classic CAN 500 kbit/s: standard + extended frames, CRC15, ACK, stuff error, bus load |
| `pico_i2c_bme280_timing` | Pico I2C0 + BME280 | Logic 2 CSV: transactions, address NAK, UM10204 Fast-mode tLOW/tHIGH (pass and fail capture) |
| `nicenano_ws2812` | nice!nano (nRF52840) PWM | sigrok `.sr`: WS2812 GRB pixels, T0H/T1H/reset windows (pass and fail capture) |
| `ch32v003_onewire_ds18b20` | CH32V003 PD6 + DS18B20 | Logic 2 CSV, 1-Wire: reset/presence, Read ROM, scratchpad, CRC8, 25.0625 C; missing sensor |
| `h743_quadrature` | WeAct H743 TIM1 encoder | VCD: 4x count, reversals, 80 ns glitch found, `GlitchFilterEntry` built with `saleae.automation` |
| `esp32s3_servo_pwm` | ESP32-S3 LEDC 50 Hz | Logic 2 binary export: period, pulse widths 1.0/1.5/2.0 ms within one 14-bit LEDC tick |
| `h562_swd_idcode` | WeAct H562 SWD | Logic 2 CSV: line reset, JTAG-to-SWD, DPIDR (Arm DP v2), power-up handshake, WAIT + retry, parity |
| `k210_i2s_mic` | K210 I2S0 | VCD, Philips I2S 48 kHz 16-bit: 1 kHz tone at -6 dBFS on the left, right silent |
| `esp32c3_boot_uart` | ESP32-C3 U0TXD | Logic 2 CSV: ROM boot log with two 100 ns glitches: glitch scan, damaged decode, filter, autobaud |
| `pico2_i2c_hla` | Pico 2 I2C1 + BME280 | Logic 2 HLA (`bme280_hla/`) run on the host by `tools/hla_host.py`: register names, chip id, raw temperature |
| `yocto_gpio_latency` | Yocto SoC (RPi 4 / i.MX8, libgpiod) | GPIO in-to-out latency p50/p99/max vs 100 us budget, one outlier; round trip CSV, VCD, binary, `.sr` |
| `rust_capture_parser` | BlackPill USART2 | Rust (32_17): no_std Logic 2 binary parser + UART decoder, host tests, thumbv7em-none-eabihf build |
| `zig_capture_parser` | Pico SPI0 SD card | Zig (32_24): Logic 2 binary parser + SPI decoder, `zig test`, Cortex-M0+ object with an exported C function |

Templates: `./saleae-box new <kind> <name>`, then the test in the last column (all run in `tests/test_smoke.sh`).

| Kind | What you get | Test |
|---|---|---|
| `capture_script` | `<name>.py`: connect, timed capture, analyzer, data-table + raw CSV + `.sal` export, `--plan`, `--config analyzers.json --key ...`; exit 77 without a server | `saleae-box python <name>.py --plan` |
| `trigger_capture` | automation capture on a digital trigger (edge or pulse width), after-trigger time, glitch filter, threshold | pytest (API objects, plan; live = exit 77) |
| `board_analyzers` | `analyzers.json` for one board (pins, channels, settings) + validator | pytest |
| `hla_extension` | Logic 2 HLA (`extension.json`, `HighLevelAnalyzer.py`): UART bytes to text lines, settings | pytest on the host harness |
| `capture_test` | capture-to-pytest: `expect.json` + tests; `--cap-file` for a real export | pytest |
| `spi_check` | expected SPI transactions (`x` = don't care) + max clock | pytest |
| `i2c_register_map` | register names, expected accesses, UM10204 timing | pytest |
| `can_check` | CAN IDs, DLC, period, CRC/stuff/ACK errors | pytest |
| `timing_budget` | edge-to-edge latency percentile and worst case vs budget | pytest |
| `pwm_check` | PWM frequency, duty, period jitter | pytest |
| `ws2812_check` | WS2812 timing, pixel count, colours | pytest |
| `glitch_scan` | glitches on every channel, JSON report + Logic 2 glitch-filter entries | pytest |
| `rust_decoder` | no_std Rust PWM measurement on a Logic 2 binary channel (Rust from 32_17) | `saleae-box run bash test.sh` (exit 3: no 32_17) |
| `zig_decoder` | Zig glitch/edge counter + Cortex-M33 object (Zig from 32_24) | `saleae-box run bash test.sh` (exit 3: no 32_24) |

Python templates: `saleae-box python -m pytest -q -p no:cacheprovider <name>`.

Languages: Rust and Zig get examples and templates (capture parsers/decoders: host tests + cross builds, toolchains
reached in 32_17/32_24). A Rust automation client is not included: logic2-automation is a gRPC API with a Python
client only; a Rust client would need tonic/prost and the `.proto` from the Saleae repo (crate downloads), not done.
Bend 2: not supported yet, because its toolchain ID (32_31_bend) does not exist here, so a Bend decoder or CRC law could
not be checked, and boxtool's `examples test` counts the skip (exit 3) as FAIL, so a Bend example would make `test --all`
fail on a machine without 32_31.

Formats: the Logic 2 binary export reader/writer follows Saleae's documented digital v0 layout and the `.sr` writer
the sigrok session v2 layout; neither was checked against files written by Logic 2 or PulseView here.

## Configuration and environment variables

| Variable | Default | Meaning |
|---|---|---|
| `BOXT_OUT` | same ID path on idisk03, else the ID folder | output root (`build/`, `log/`); also settable in `config/local.env` |
| `BOXT_JOBS` | 8 (maximum) | parallel jobs |
| `BOXT_MIN_FREE_GB` | 8 | pause builds while less RAM is free |
| `BOXT_RAM_WAIT_MAX` | 3600 | give up waiting for RAM after this many seconds |
| `BOXT_NET_TIMEOUT` | 3600 | seconds for one download |
| `BOXT_PLATFORM` | detected (`linux-x64`) | override the platform |
| `GITHUB_TOKEN` | unset | optional; lifts the GitHub API limit for `update --check` |
| `BOX_INTEGRATION` | 1 | `0` = standalone: ignore `$BOX`/`$BOX_V3`, keep output in this folder |
| `NO_COLOR` | unset | set to print plain text (colour is only used on a terminal anyway) |
| `SALEAE_AUTOMATION_PORT` | 10430 | Logic 2 automation port |
| `BOX_EMBEDDED_RUST`, `BOX_MICROZIG` | the sibling folders | 32_17_embedded_rust / 32_24_microzig for the Rust and Zig examples and templates |
| `SALEAE_BOX_GATE_ONLY` | unset | `1`: install skips the bootstrap (tests) |
| `SALEAE_BOX_LICENSED_TSV`, `_TOFU_TSV`, `_LICENCE_RECORD`, `_INSTALL_DIR`, `_DOWNLOAD_DIR` | `config/licensed.tsv`, `config/pins.local.tsv`, `config/local-licence.txt`, `install/`, `cache/downloads` | test hooks to run the licensed install on fixtures |
| `BOX_NATIVE_OFF_SALEAE` | unset | `1` skips native mode for one shell (old name `SALEAE_BOX_NATIVE_OFF` still honoured) |
| `BOX_SALEAE` | set by `box_env.sh` | path of this ID, used by the native snippet |

## Where files go

| What | Where |
|---|---|
| Source, launcher, `tools/saleae_export.py`, examples, templates, `config/` | this ID |
| Tools | `.pixi/` (268 MB: python, grpcio, protobuf, logic2-automation), `.bin/` (77 MB pixi); after install `install/logic2-2.4.48/` (AppImage 213 MB + extracted root about 550 MB, estimated; 0 now) |
| Cache | `cache/` (142 MB pixi/uv cache; `CACHEDIR.TAG`); the AppImage download goes to `cache/downloads` |
| Build output and logs | `$BOX_V3/30_39_tools/32_embedded/32_16_saleae/{build,log}` (0.1 MB) |
| Your records | `config/pins.local.tsv`, `config/local-licence.txt` (written by install, gitignored) |

ID size now: 486 MB.

## Native mode

`./saleae-box native` writes `native/native.{zsh,bash}` and `native/bin/{Logic2,saleae-python,saleae-parse}` (through
the launcher). Load it in every shell (zsh, bash, fish) with `box native enable saleae --apply`: it runs `./saleae-box
native` when the files are missing and rebuilds `box_env.d/native.*` (without `--apply` it only shows the plan; `box
native disable saleae --apply` undoes it). `BOX_NATIVE_OFF_SALEAE=1` skips it for one shell (the old
`SALEAE_BOX_NATIVE_OFF` still works for now). Without Box, source `native/native.zsh` or `native/native.bash` from
your shell rc.

## Tests

```sh
./saleae-box test --all         # smoke + dry-run + examples
tests/test_smoke.sh             # API import, parser, convert/decode, all 14 templates; Logic 2 if installed (SKIP otherwise)
tests/test_dry_run.sh           # every command in --dry-run + install logic on fixtures + shellcheck
tests/test_install_logic.sh     # EULA gate, TOFU, AppImage extraction on a fixture (no Saleae binary)
```

Last known (2026-10-29): doctor 13 ok / 2 warn / 0 fail; examples 18/18 (live capture SKIP); smoke 17 ok, 2 skip
(Logic 2 not installed, no automation server); dry-run 35/35 (shellcheck included); install logic 12/12.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `install` exits 2 and prints the licence URL | expected without `--accept-license`; read the terms, then pass the flag |
| sha256 mismatch on a later install | aborts and keeps the `.part` file; if Saleae re-released the file, update `config/licensed.tsv` and the TOFU pin deliberately |
| `automation-ping` fails | start `./saleae-box logic2 --automation` first (port 10430, or set `SALEAE_AUTOMATION_PORT`) |
| `automation_blackpill_spi` reports SKIP / script exits 77 | no automation server running; not a failure |
| Logic 2 cannot see the analyser | install the udev rules (below), re-plug the device |

## Limitations / needs you

- **Licence (you):** read <https://support.saleae.com/faq/general-faq/license> (URL also printed by `./saleae-box licence`), then run `$BOX_SALEAE/saleae-box install --accept-license`.
- **udev rules (sudo, run these yourself):**

```sh
# a) Saleae's own file from the AppImage (after install --accept-license)
sudo cp "$(find "$BOX_SALEAE/install/logic2/root" -name '*Saleae*.rules' | head -1)" /etc/udev/rules.d/99-SaleaeLogic.rules
# b) or the minimal file written for this ID (vendor 21a9, uaccess for the seat user)
sudo cp "$BOX_SALEAE/udev/70-box-saleae.rules" /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

- **Hardware:** a Saleae analyser is needed for live captures. Not verified here: Logic 2 itself, any live capture, the
  trigger/timed capture templates against a device, HLAs inside Logic 2 (only in the host harness), and files written by
  Logic 2 / PulseView (all captures here are generated).
- **Other OSes:** only the Linux x64 AppImage is pinned. Saleae also ships Linux arm64, macOS dmg and Windows exe: add rows to `config/licensed.tsv` (dmg/exe need an unpack hook). The pixi env is locked for Linux, macOS and Windows, so the parser and scripts run everywhere.

## Scripts

Each script has a `[scripts.*]` descriptor in `.box.toml` (`box scripts show 32_16`; `box scripts check 32_16` must stay clean).

| File | Purpose |
|---|---|
| `saleae-box` | launcher (POSIX sh): bootstraps the pinned pixi, keeps caches in this folder, then runs `lib/` |
| `lib/boxtool.bash` | shared launcher framework (boxtool 3: bootstrap, pinned downloads, pixi env, every common command); byte-identical copy of `$BOX/00_09_meta/05_policy/templates/tool/lib/boxtool.bash` (edit there, then sync) |
| `lib/saleae.bash` | this tool's part: licence gate, fetch, extract, `logic2`, `parse` |
| `tools/saleae_export.py` | Logic 2 export parser + software UART decoder (stdlib only) |
| `tools/decoders.py` | protocol decoders and timing checks (`decode`) |
| `tools/capfmt.py` | Logic 2 CSV, VCD, Logic 2 binary, sigrok `.sr` read/write (`convert`) |
| `tools/logicsim.py` | ideal bus waveforms for fixtures (examples, templates) |
| `tools/hla_host.py` | stand-in for Logic 2's `saleae.analyzers` to run HLAs on the host (`hla`) |
| `examples/*/example.sh` | the 18 examples |
| `tests/test_smoke.sh`, `tests/test_dry_run.sh`, `tests/test_install_logic.sh` | smoke, dry-run/shellcheck, EULA-gate/TOFU logic on fixtures |
| `native/` | written by `./saleae-box native`; regenerate, do not edit |

## Links

- logic2-automation: <https://github.com/saleae/logic2-automation>
- Saleae licence: <https://support.saleae.com/faq/general-faq/license>; terms: <https://www.saleae.com/policies/terms-of-service>
- pixi: <https://github.com/prefix-dev/pixi>
- History: `NOTES.md`. Report: `$BOX/00_09_meta/02_logs/2026_10_25_embedded_tools2_report.md`.
- Sibling tools: `32_11_serial` (UART monitors), `32_12_segger` (SystemView/RTT).
