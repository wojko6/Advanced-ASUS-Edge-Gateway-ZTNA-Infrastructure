#!/bin/sh
# PR197: verify that packaged executable matches the installer pin and ARM ABI.
set -eu
ROOT="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
BIN="$ROOT/router/bin/edge-dns-supervisor"
INSTALL="$ROOT/scripts/install.sh"
EXPECTED="26f3615a99448469718f682bde6960e27e30b9466ecfc427c7e392c317103740"

fail() { echo "FAIL: $1" >&2; exit 1; }
[ -f "$BIN" ] && [ ! -L "$BIN" ] && [ -s "$BIN" ] || fail 'missing/unsafe ARM artifact'
[ -f "$INSTALL" ] || fail 'missing installer'
command -v sha256sum >/dev/null 2>&1 || fail 'sha256sum unavailable'
command -v readelf >/dev/null 2>&1 || fail 'readelf unavailable'

PIN="$(sed -n 's/^SUPERVISOR_SHA256_EXPECTED="\([0-9a-f]*\)"$/\1/p' "$INSTALL")"
[ "$PIN" = "$EXPECTED" ] || fail 'installer SHA pin mismatch'
printf '%s  %s\n' "$EXPECTED" "$BIN" | sha256sum -c - >/dev/null || fail 'ARM SHA-256 mismatch'

HEADER="$(readelf -h "$BIN")" || fail 'readelf header failed'
printf '%s\n' "$HEADER" | grep -Eq 'Class:[[:space:]]*ELF32' || fail 'not ELF32'
printf '%s\n' "$HEADER" | grep -Eq 'Machine:[[:space:]]*ARM' || fail 'not ARM'
printf '%s\n' "$HEADER" | grep -Fq 'Version5 EABI' || fail 'not EABI5'
printf '%s\n' "$HEADER" | grep -Fq 'soft-float ABI' || fail 'not soft-float ABI'
if readelf -l "$BIN" | grep -q 'INTERP'; then
    fail 'ARM binary is dynamically linked'
fi
printf '%s\n' 'ARMV7_ARTIFACT_CONTRACT=PASS'
