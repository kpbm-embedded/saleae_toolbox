# shellcheck shell=bash disable=SC2015,SC2034  # d_* return 0; TOOL_* are read by boxtool.bash
# saleae-box: tool part (hooks for lib/boxtool.bash). Saleae Logic 2 (proprietary AppImage,
# user-accepted EULA, extracted so no FUSE is needed) + Saleae's open-source logic2-automation
# Python API (PyPI, Apache-2.0) in the pixi env, export parsers and analyzer templates.
# LICENCE: Logic 2 is downloaded only by `./saleae-box install --accept-license`, which records
# who accepted (config/local-licence.txt, gitignored) and pins the sha256 on first use
# (config/pins.local.tsv, gitignored; Saleae publishes no checksum; a later mismatch aborts).
# The licensed table is config/licensed.tsv, NOT config/pins.tsv, so `bootstrap` never fetches it.
# SAFETY: a logic analyser only reads; `list` is lsusb only.
TOOL_TITLE="32_16_saleae: Saleae Logic $(awk -F'\t' '$1=="logic2"{print $2; exit}' "${BOXT_ROOT:?}/config/licensed.tsv") (user-accepted EULA) + logic2-automation 1.0.11"
TOOL_INSTALL_WHAT="Logic 2 (only with --accept-license)"
TOOL_HELP_USE="  install --accept-license   YOU accept Saleae's licence; downloads the pinned Logic 2 AppImage
                          (without the flag: bootstrap only, prints the licence URL and exits 2)
  licence                 the licence URL and what has been accepted on this machine
  list                    read-only: Saleae analysers on USB (lsusb 21a9:*)
  logic2 [args]           start Logic 2 (extracted AppImage); automation: logic2 --automation
  automation-ping [port]  is Logic 2's automation server up? (127.0.0.1:10430)
  parse <file.csv|.vcd>   summarise a Logic 2 export (tools/saleae_export.py)
  decode <cap> <proto> --map ROLE=ch,...   uart spi i2c can onewire ws2812 pwm quadrature i2s swd glitch
                          (tools/decoders.py; cap: .csv .vcd .sr or a Logic 2 binary export dir)
  convert <in> <out> [--samplerate HZ]     between Logic 2 CSV, VCD, Logic 2 binary (dir), sigrok .sr
  hla <ext dir> <cap> <i2c|uart|spi> --map ...   run a Logic 2 HLA extension on the host (tools/hla_host.py)
  python [args]           the env's Python with saleae.automation"
hook_help() { # printed after boxtool's help: tool-specific examples and environment
  cat <<EOF

tool examples
  ./$BOXT_NAME parse capture.csv --uart 'Channel 0:115200'
  ./$BOXT_NAME logic2 --automation & ./$BOXT_NAME automation-ping
  ./$BOXT_NAME decode cap.vcd i2c --map SCL=SCL,SDA=SDA --json
  ./$BOXT_NAME convert cap.csv cap.sr --samplerate 10000000
tool environment
  SALEAE_AUTOMATION_PORT  Logic 2 automation port (10430)
  BOX_EMBEDDED_RUST, BOX_MICROZIG  32_17_embedded_rust / 32_24_microzig IDs for the Rust and Zig
                          examples (default: the sibling folder; examples exit 3 when missing)
  SALEAE_BOX_GATE_ONLY=1  install: skip the bootstrap (tests)
  SALEAE_BOX_LICENSED_TSV, SALEAE_BOX_TOFU_TSV, SALEAE_BOX_LICENCE_RECORD, SALEAE_BOX_INSTALL_DIR,
  SALEAE_BOX_DOWNLOAD_DIR  test hooks; default config/licensed.tsv, config/pins.local.tsv, ...
EOF
}
# shellcheck source-path=SCRIPTDIR source=boxtool.bash
. "$BOXT_ROOT/lib/boxtool.bash"

LICENSED=${SALEAE_BOX_LICENSED_TSV:-$CONFIG/licensed.tsv}   # tests point these at fixtures
TOFU=${SALEAE_BOX_TOFU_TSV:-$CONFIG/pins.local.tsv}
LICREC=${SALEAE_BOX_LICENCE_RECORD:-$CONFIG/local-licence.txt}
LINST=${SALEAE_BOX_INSTALL_DIR:-$INST}
LDL=${SALEAE_BOX_DOWNLOAD_DIR:-$DL}
AUTOMATION_PORT=${SALEAE_AUTOMATION_PORT:-10430}

sibling_id() { # ENV_VAR FOLDER MARKER -> another tool ID: the variable's folder (or one above it that
  # holds MARKER), else ../FOLDER, else nothing. Used for toolchains this ID reaches but never installs.
  local d=${!1:-} i
  for i in 1 2 3; do
    [[ -n "$d" ]] && [[ -e "$d/$3" ]] && { (cd -P "$d" && pwd -P); return 0; }
    d=${d%/*}
  done
  if [[ -e "$ROOT/../$2/$3" ]]; then (cd -P "$ROOT/../$2" && pwd -P); fi
}
RUST_ID=$(sibling_id BOX_EMBEDDED_RUST 32_17_embedded_rust rust-box)
ZIG_ID=$(sibling_id BOX_MICROZIG 32_24_microzig microzig-box)

# ---------- licensed table: name version platform digest(sha256:..|-) url licence-urls title ----------
lic_rows() { [[ -r "$LICENSED" ]] && awk -F'\t' '!/^[[:space:]]*#/ && NF>=6' "$LICENSED"; true; }
lic_names() { lic_rows | awk -F'\t' -v p="$PLATFORM" '$3==p {print $1}' | awk '!s[$0]++'; }
lic_get() { lic_rows | awk -F'\t' -v n="$1" -v p="$PLATFORM" -v f="$2" '$1==n && $3==p {print $f; exit}'; }
lic_file() { local u; u=$(lic_get "$1" 5); printf '%s/%s' "$LDL" "$(basename "${u%%\?*}")"; }
lic_dir() { printf '%s/%s-%s' "$LINST" "$1" "$(lic_get "$1" 2)"; }
lic_installed() { [[ -e "$(lic_dir "$1")/.boxt-ok" ]]; }

tofu_get() { [[ -r "$TOFU" ]] && awk -F'\t' -v n="$1" -v v="$2" '$1==n && $2==v {print $4; exit}' "$TOFU"; true; }
tofu_check() { # name version file -> 0 ok (recorded or matching), 1 mismatch
  local n=$1 v=$2 f=$3 want have_s
  have_s=$(sha_of sha256 "$f")
  want=$(tofu_get "$n" "$v")
  if [[ -z "$want" ]]; then
    mkdir -p "$(dirname "$TOFU")"
    [[ -e "$TOFU" ]] || printf '# name\tversion\tfile\tsha256\tdate  (trust on first use, written by saleae-box install; gitignored)\n' >"$TOFU"
    printf '%s\t%s\t%s\t%s\t%s\n' "$n" "$v" "$(basename "$f")" "$have_s" "$(date -Iseconds)" >>"$TOFU"
    info "$n $v: sha256 $have_s recorded (TOFU, $(basename "$TOFU"))"
    return 0
  fi
  if [[ "$want" = "$have_s" ]]; then info "$n $v: sha256 matches the pin from first use"; return 0; fi
  warn "$n $v: sha256 $have_s differs from the first-use pin $want"
  return 1
}

licence_urls() { lic_rows | awk -F'\t' -v p="$PLATFORM" '$3==p {n=split($6,a," "); for(i=1;i<=n;i++) print $1": "a[i]}' | awk '!s[$0]++'; }
print_licences() {
  cat <<EOF
Saleae Logic 2 is proprietary (Saleae Software & SDK License Agreement; the same text ships in the
AppImage's license folder). Read and accept it yourself before installing:
$(licence_urls | sed 's/^/  /')
  (the logic2-automation Python API in the pixi env is Apache-2.0 and is installed by bootstrap)
Then run:  ./$NAME install --accept-license        (records your acceptance in config/local-licence.txt)
EOF
}
record_acceptance() {
  [[ "$DRY" = 1 ]] && { printf '+ record acceptance -> %s\n' "$LICREC"; return 0; }
  mkdir -p "$(dirname "$LICREC")"
  {
    printf '# %s licence acceptance (gitignored; written by ./%s install --accept-license)\n' "${LICREC##*/}" "$NAME"
    printf 'accepted_by=%s@%s\naccepted_at=%s\n' "${USER:-$(id -un)}" "$(hostname 2>/dev/null || echo host)" "$(date -Iseconds)"
    local n; for n in "$@"; do printf 'package=%s %s %s\n' "$n" "$(lic_get "$n" 2)" "$(lic_get "$n" 6)"; done
    printf '\n'
  } >>"$LICREC"
}

fetch_licensed() { # name -> file in cache/downloads (published digest if any + TOFU sha256)
  local n=$1 url dig f
  url=$(lic_get "$n" 5); dig=$(lic_get "$n" 4); f=$(lic_file "$n")
  [[ -n "$url" ]] || die "no licensed entry for '$n' on $PLATFORM"
  if [[ -f "$f" ]]; then
    tofu_check "$n" "$(lic_get "$n" 2)" "$f" || die "$n: cached $f does not match the first-use sha256; inspect it, then move it to the Trash"
    return 0
  fi
  info "download $n $(lic_get "$n" 2): $url"
  if [[ "$DRY" = 1 ]]; then printf '+ curl -fL %s -> %s (sha256 %s)\n' "$url" "$f" "$([[ "$dig" = - ]] && echo 'TOFU' || echo "$dig")"; return 0; fi
  mkdir -p "$LDL"; cachedir_tag "$(dirname "$LDL")"
  curl -fL -sS --retry 3 --connect-timeout 30 --max-time "$NET_TIMEOUT" -o "$f.part" "$url" || die "download failed: $url"
  if head -c 200 "$f.part" | grep -i '<html' >/dev/null; then die "$n: got an HTML page instead of the AppImage; kept $f.part"; fi
  if [[ "$dig" != - ]]; then
    [[ "$(sha_of sha256 "$f.part")" = "${dig#sha256:}" ]] || die "$n: sha256 differs from config/licensed.tsv; kept $f.part"
  fi
  tofu_check "$n" "$(lic_get "$n" 2)" "$f.part" || die "$n: sha256 mismatch against the first-use pin; kept $f.part (abort)"
  mv "$f.part" "$f"
}

# AppImage: copied into install/logic2-<ver>/, extracted once (no FUSE at run time)
unpack_licensed() {
  local n=$1 dir img
  dir=$(lic_dir "$n")
  [[ -e "$dir/.boxt-ok" ]] && return 0
  info "install $n -> $dir"
  if [[ "$DRY" = 1 ]]; then printf '+ copy %s -> %s; --appimage-extract -> %s/root\n' "$(lic_file "$n")" "$dir" "$dir"; return 0; fi
  mkdir -p "$LINST"
  [[ -e "$dir" ]] && trash_paths "incomplete install of $n" "$dir"
  unpack "$(lic_file "$n")" appimage "$dir"
  img="$dir/$(basename "$(lic_file "$n")")"
  info "extracting $(basename "$img") (no FUSE needed afterwards)"
  (cd "$dir" && "$img" --appimage-extract >/dev/null) || die "$n: --appimage-extract failed"
  mv "$dir/squashfs-root" "$dir/root"
  [[ -x "$dir/root/AppRun" ]] || die "$n: extracted AppImage has no AppRun"
  printf 'name=%s\nversion=%s\nurl=%s\nsha256=%s\ndate=%s\n' "$n" "$(lic_get "$n" 2)" "$(lic_get "$n" 5)" \
    "$(tofu_get "$n" "$(lic_get "$n" 2)")" "$(date -Iseconds)" >"$dir/.boxt-ok"
  ln -sfn "$(basename "$dir")" "$LINST/$n"
}

# install [--accept-license]: replaces boxtool's install (which knows no licence flag).
# Without the flag the open-source part (pixi env with logic2-automation) is still bootstrapped.
tool_install() {
  local accept=0 n names=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --accept-license|--accept-licence) accept=1 ;;
      --no-demos|--with-demos|--all) ;;
      *) usage_error "install: unknown option $1" ;;
    esac; shift
  done
  if [[ "$accept" != 1 ]]; then
    [[ "${SALEAE_BOX_GATE_ONLY:-0}" = 1 ]] || cmd_bootstrap
    print_licences >&2
    usage_error "refused: Logic 2 licence not accepted (add --accept-license after reading it); the open-source part is bootstrapped"
  fi
  mapfile -t names < <(lic_names)
  [[ ${#names[@]} -gt 0 ]] || die "nothing to install for $PLATFORM (only the Linux x64 AppImage is pinned; README 'Other OSes')"
  [[ "${SALEAE_BOX_GATE_ONLY:-0}" = 1 ]] || cmd_bootstrap
  record_acceptance "${names[@]}"
  cachedir_tag "$LINST"
  for n in "${names[@]}"; do fetch_licensed "$n"; unpack_licensed "$n"; done
  [[ "$DRY" = 1 ]] || { [[ "$LINST" = "$INST" ]] && cmd_native; info "install done: ./$NAME doctor; udev rules: README 'udev' (sudo, you run it)"; }
}
tool_cmd_licence() {
  print_licences
  if [[ -r "$LICREC" ]]; then echo "accepted on this machine ($LICREC):"; grep -E '^(accepted_|package=)' "$LICREC" | sed 's/^/  /'
  else echo "not accepted on this machine yet"; fi
}
tool_cmd_license() { tool_cmd_licence "$@"; }

logic2_run() { local r="$LINST/logic2/root/AppRun"; [[ -x "$r" ]] && printf '%s' "$r"; true; }

hook_env() {
  # Logic 2 (Electron) keeps its settings under XDG/HOME-based dirs: inside the ID
  export XDG_CONFIG_HOME="$ROOT/cache/xdg-config" XDG_DATA_HOME="$ROOT/cache/xdg-data" XDG_CACHE_HOME="$ROOT/cache/xdg-cache"
  export PIP_CACHE_DIR="$ROOT/cache/pip" PYTHONDONTWRITEBYTECODE=1
  mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME" 2>/dev/null || true
  export SALEAE_BOX_ROOT="$ROOT" SALEAE_AUTOMATION_PORT="$AUTOMATION_PORT" PYTHONPATH="$ROOT/tools"
  LOGIC2=$(logic2_run); export LOGIC2
  export SALEAE_RUST_BOX="${RUST_ID:+$RUST_ID/rust-box}" SALEAE_ZIG_BOX="${ZIG_ID:+$ZIG_ID/microzig-box}"
}
hook_bootstrap() { cachedir_tag "$ROOT/cache"; }
hook_status() {
  local n
  for n in $(lic_names); do
    printf '  %-22s %-12s %-9s %s\n' "$n" "$(lic_get "$n" 2)" licensed "$(lic_installed "$n" && echo "installed $(human_size "$(lic_dir "$n")")" || echo 'not installed (needs --accept-license)')"
  done
  printf '  %-22s %s\n' licence "$([[ -r "$LICREC" ]] && echo "accepted ($(grep -c '^accepted_at' "$LICREC")x)" || echo 'not accepted')"
}

hook_doctor() {
  local v n
  v=$(python -c 'import importlib.metadata as m; print(m.version("logic2-automation"))' 2>/dev/null) && d_ok "logic2-automation $v (Apache-2.0)" || d_fail "logic2-automation missing in the pixi env"
  python -c 'from saleae import automation; automation.Manager' 2>/dev/null && d_ok "saleae.automation imports (grpc)" || d_fail "saleae.automation import failed"
  python -I -c 'import sys; sys.path.insert(0, sys.argv[1]); import saleae_export' "$ROOT/tools" 2>/dev/null && d_ok "tools/saleae_export.py imports" || d_fail "tools/saleae_export.py broken"
  for n in $(lic_names); do
    if lic_installed "$n"; then d_ok "$n $(lic_get "$n" 2) installed (user-accepted EULA)"
    else d_warn "$n $(lic_get "$n" 2) not installed: proprietary, needs './$NAME install --accept-license' by you"; fi
  done
  if [[ -e /etc/udev/rules.d/99-SaleaeLogic.rules ]] || [[ -e /usr/lib/udev/rules.d/99-SaleaeLogic.rules ]] || [[ -e /etc/udev/rules.d/70-box-saleae.rules ]]; then
    d_ok "Saleae udev rules present"
  else d_warn "Saleae udev rules not installed: analysers need root (README 'udev', sudo, you run it)"; fi
  [[ -r "$ROOT/udev/70-box-saleae.rules" ]] && d_ok "udev/70-box-saleae.rules shipped" || d_fail "udev/70-box-saleae.rules missing"
  have lsusb && d_ok "lsusb available (list)" || d_warn "lsusb missing"
  python -I -c 'import sys; sys.path.insert(0, sys.argv[1]); import decoders, capfmt, logicsim, hla_host' "$ROOT/tools" 2>/dev/null \
    && d_ok "tools/decoders.py, capfmt.py, logicsim.py, hla_host.py import" || d_fail "tools/ decoders broken"
  [[ -n "$RUST_ID" ]] && d_ok "Rust via 32_17_embedded_rust ($RUST_ID)" || d_warn "32_17_embedded_rust not found (BOX_EMBEDDED_RUST): Rust examples exit 3"
  [[ -n "$ZIG_ID" ]] && d_ok "Zig via 32_24_microzig ($ZIG_ID)" || d_warn "32_24_microzig not found (BOX_MICROZIG): Zig examples exit 3"
}

hook_native_bins() {
  echo "Logic2 @logic2"
  echo "saleae-python @python"
  echo "saleae-parse @parse"
  echo "saleae-decode @decode"
}

tool_cmd_logic2() {
  activate
  [[ "$DRY" = 1 ]] && { printf '+ Logic2 AppRun %s\n' "$*"; return 0; }
  [[ -n "$LOGIC2" ]] || die "Logic 2 not installed (proprietary: read './$NAME licence', then ./$NAME install --accept-license)"
  exec "$LOGIC2" "$@"
}
tool_cmd_python() { activate; [[ "$DRY" = 1 ]] && { printf '+ python %s\n' "$*"; return 0; }; exec python "$@"; }
tool_cmd_parse() {
  [[ $# -ge 1 ]] || usage_error "usage: ./$NAME parse <export.csv|capture.vcd> [--json] [--uart CH:BAUD]"
  activate; [[ "$DRY" = 1 ]] && { printf '+ python tools/saleae_export.py %s\n' "$*"; return 0; }
  exec python -I "$ROOT/tools/saleae_export.py" "$@"
}
tool_cmd_decode() {
  [[ $# -ge 2 ]] || usage_error "usage: ./$NAME decode <capture> <protocol> --map ROLE=ch,... [--baud N] [--json]"
  activate; [[ "$DRY" = 1 ]] && { printf '+ python tools/decoders.py %s\n' "$*"; return 0; }
  exec python -I "$ROOT/tools/decoders.py" "$@"
}
tool_cmd_convert() {
  [[ $# -ge 2 ]] || usage_error "usage: ./$NAME convert <in> <out> [--samplerate HZ]"
  activate; [[ "$DRY" = 1 ]] && { printf '+ python tools/capfmt.py convert %s\n' "$*"; return 0; }
  exec python -I "$ROOT/tools/capfmt.py" convert "$@"
}
tool_cmd_hla() {
  [[ $# -ge 3 ]] || usage_error "usage: ./$NAME hla <extension dir> <capture> <i2c|uart|spi> --map ROLE=ch,... [--setting k=v]"
  activate; [[ "$DRY" = 1 ]] && { printf '+ python tools/hla_host.py %s\n' "$*"; return 0; }
  exec python -I "$ROOT/tools/hla_host.py" "$@"
}
tool_cmd_automation-ping() {
  local port=${1:-$AUTOMATION_PORT}
  [[ "$DRY" = 1 ]] && { printf '+ probe 127.0.0.1:%s\n' "$port"; return 0; }
  if (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null; then echo "Logic 2 automation server is listening on 127.0.0.1:$port"
  else echo "nothing listens on 127.0.0.1:$port (start: ./$NAME logic2 --automation)"; return 1; fi
}
tool_cmd_list() {
  if [[ "$DRY" = 1 ]]; then echo "+ lsusb (filter 21a9:*)"; return 0; fi
  have lsusb || die "lsusb not found (usbutils)"
  echo "== Saleae logic analysers on USB (vendor 21a9, read-only lsusb)"
  lsusb | grep -i ' 21a9:' || echo "(none)"
  echo "# clones with Cypress FX2 (04b4:8613 / 0925:3881) are NOT supported by Logic 2 (EULA); use sigrok/PulseView"
}

boxt_main_saleae() {
  case "${1:-help}" in
    install) shift; tool_install "$@" ;;
    *) boxt_main "$@" ;;
  esac
}
boxt_main_saleae "$@"
