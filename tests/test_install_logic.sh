#!/usr/bin/env bash
# The licensed-install logic WITHOUT Saleae's AppImage: EULA gate refusal, dry-run install, a
# fixture "AppImage" over file:// (TOFU sha256 record + recheck + mismatch abort, HTML instead of
# the AppImage, --appimage-extract into install/logic2-<ver>/root), wrappers when not installed.
# State goes to a temp dir through the SALEAE_BOX_* test hooks; config/ and install/ are untouched.
# Usage: tests/test_install_logic.sh
# shellcheck disable=SC2015  # ok() always returns 0
set -uo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd -P)
L="$HERE/saleae-box"
pass=0; failn=0
ok()  { printf 'ok    %s\n' "$*"; pass=$((pass+1)); }
bad() { printf 'FAIL  %s\n' "$*"; failn=$((failn+1)); }
tmp=$(mktemp -d)
cleanup() { if command -v trash-put >/dev/null; then trash-put "$tmp"; fi; }   # own temp dir; never rm
trap cleanup EXIT
export SALEAE_BOX_GATE_ONLY=1   # skip the (already tested) pixi bootstrap inside install

out=$("$L" install 2>&1); rc=$?
[[ "$rc" = 2 ]] && grep -q 'https://support.saleae.com/faq/general-faq/license' <<<"$out" && grep -q 'refused: Logic 2 licence not accepted' <<<"$out" \
  && ok "EULA gate refuses without --accept-license (exit 2, URL printed)" || bad "EULA gate (rc=$rc)"

before=$(find "$HERE/cache/downloads" "$HERE/install" "$HERE/config" -type f 2>/dev/null | sort | md5sum)
out=$("$L" --dry-run install --accept-license 2>&1); rc=$?
after=$(find "$HERE/cache/downloads" "$HERE/install" "$HERE/config" -type f 2>/dev/null | sort | md5sum)
[[ "$rc" = 0 ]] && grep -q 'curl -fL https://downloads2.saleae.com/logic2/Logic-2.4.48-linux-x64.AppImage' <<<"$out" && grep -q 'sha256 TOFU' <<<"$out" \
  && grep -q 'appimage-extract' <<<"$out" && [[ "$before" = "$after" ]] && ok "dry-run install: pinned URL, TOFU, extract step, nothing written" || { bad "dry-run install (rc=$rc)"; tail -4 <<<"$out"; }

# fixture AppImage: a shell script that implements --appimage-extract like the type-2 runtime
mkdir -p "$tmp/state"
cat >"$tmp/Logic-0.0.1-linux-x64.AppImage" <<'FX'
#!/bin/sh
if [ "${1:-}" = --appimage-extract ]; then
  mkdir -p squashfs-root/resources && printf '#!/bin/sh\necho "Logic 2 fixture $*"\n' >squashfs-root/AppRun && chmod +x squashfs-root/AppRun
  printf 'SUBSYSTEM=="usb", ATTRS{idVendor}=="21a9", MODE="0666"\n' >squashfs-root/resources/99-SaleaeLogic.rules
  exit 0
fi
echo "run me extracted"; exit 1
FX
chmod +x "$tmp/Logic-0.0.1-linux-x64.AppImage"
sha=$(sha256sum "$tmp/Logic-0.0.1-linux-x64.AppImage" | cut -d' ' -f1)
printf 'logic2\t0.0.1\tlinux-x64\t-\tfile://%s\thttps://support.saleae.com/faq/general-faq/license\tfixture\n' "$tmp/Logic-0.0.1-linux-x64.AppImage" >"$tmp/licensed.tsv"
export SALEAE_BOX_LICENSED_TSV="$tmp/licensed.tsv" SALEAE_BOX_TOFU_TSV="$tmp/state/pins.local.tsv" \
       SALEAE_BOX_LICENCE_RECORD="$tmp/state/local-licence.txt" SALEAE_BOX_INSTALL_DIR="$tmp/install" SALEAE_BOX_DOWNLOAD_DIR="$tmp/dl"
out=$("$L" install --accept-license 2>&1); rc=$?
[[ "$rc" = 0 ]] && grep -q "$sha" "$tmp/state/pins.local.tsv" 2>/dev/null && ok "first install records the TOFU sha256" || { bad "first install (rc=$rc)"; tail -5 <<<"$out"; }
[[ -x "$tmp/install/logic2-0.0.1/root/AppRun" ]] && [[ -L "$tmp/install/logic2" ]] && grep -q "sha256=$sha" "$tmp/install/logic2-0.0.1/.boxt-ok" \
  && ok "AppImage extracted to install/logic2-0.0.1/root (+ link, .boxt-ok)" || bad "extract layout"
grep -q '^accepted_by=' "$tmp/state/local-licence.txt" && grep -q '^package=logic2 0.0.1' "$tmp/state/local-licence.txt" && ok "acceptance recorded" || bad "acceptance record"
v=$("$L" logic2 --version 2>&1); grep -q 'Logic 2 fixture --version' <<<"$v" && ok "logic2 wrapper runs the extracted AppRun" || bad "logic2 wrapper: $v"
out=$("$L" install --accept-license 2>&1); rc=$?
[[ "$rc" = 0 ]] && grep -q 'matches the pin from first use' <<<"$out" && ok "reinstall: cached AppImage matches the TOFU pin" || bad "reinstall (rc=$rc)"
sed -i "s/$sha/$(printf 'f%.0s' {1..64})/" "$tmp/state/pins.local.tsv"
out=$("$L" install --accept-license 2>&1); rc=$?
[[ "$rc" != 0 ]] && grep -q 'differs from the first-use pin' <<<"$out" && ok "TOFU mismatch aborts" || bad "TOFU mismatch (rc=$rc)"
printf '<html><body>moved</body></html>\n' >"$tmp/page.AppImage"
printf 'logic2\t0.0.2\tlinux-x64\t-\tfile://%s\thttps://support.saleae.com/faq/general-faq/license\tfixture\n' "$tmp/page.AppImage" >"$tmp/licensed.tsv"
out=$("$L" install --accept-license 2>&1); rc=$?
[[ "$rc" != 0 ]] && grep -q 'HTML page instead of the AppImage' <<<"$out" && ok "HTML instead of AppImage aborts" || bad "HTML detection (rc=$rc)"
printf 'logic2\t0.0.3\tlinux-x64\tsha256:%s\tfile://%s\thttps://support.saleae.com/faq/general-faq/license\tfixture\n' "$(printf '0%.0s' {1..64})" "$tmp/Logic-0.0.1-linux-x64.AppImage" >"$tmp/licensed.tsv"
mv "$tmp/dl/Logic-0.0.1-linux-x64.AppImage" "$tmp/dl/old"
out=$("$L" install --accept-license 2>&1); rc=$?
[[ "$rc" != 0 ]] && grep -q 'sha256 differs from config/licensed.tsv' <<<"$out" && ok "published-digest mismatch aborts" || bad "published digest (rc=$rc)"
unset SALEAE_BOX_LICENSED_TSV SALEAE_BOX_TOFU_TSV SALEAE_BOX_LICENCE_RECORD SALEAE_BOX_INSTALL_DIR SALEAE_BOX_DOWNLOAD_DIR

if [[ ! -d "$HERE/install/logic2/" ]]; then
  out=$("$L" logic2 2>&1); rc=$?
  [[ "$rc" != 0 ]] && grep -q 'Logic 2 not installed' <<<"$out" && ok "logic2 fails cleanly when not installed" || bad "logic2 not installed (rc=$rc)"
fi
out=$("$L" automation-ping 59999 2>&1); rc=$?
[[ "$rc" != 0 ]] && grep -q 'nothing listens' <<<"$out" && ok "automation-ping reports a closed port" || bad "automation-ping (rc=$rc)"
echo "install-logic: $pass ok, $failn failed"
[[ "$failn" -eq 0 ]]
