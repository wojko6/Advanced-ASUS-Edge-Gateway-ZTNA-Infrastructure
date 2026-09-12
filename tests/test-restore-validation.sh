#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
TMPROOT="$(mktemp -d)"
trap 'rm -rf "$TMPROOT"' EXIT HUP INT TERM

make_valid_backup() {
    root="$TMPROOT/asus-edge-test"
    rm -rf "$root"
    mkdir -p "$root/jffs/configs"
    printf '%s\n' 'EDGE_TEST_VALUE=1' >"$root/jffs/configs/asus-edge.conf"
    (
        cd "$root"
        sha256sum ./jffs/configs/asus-edge.conf >SHA256SUMS
    )
    tar -czf "$TMPROOT/valid.tar.gz" -C "$TMPROOT" asus-edge-test
}

make_valid_backup
output="$(sh "$ROOT_DIR/scripts/restore.sh" "$TMPROOT/valid.tar.gz" --dry-run)"
printf '%s\n' "$output" | grep -F 'Verified backup contents:' >/dev/null
printf '%s\n' "$output" | grep -F 'Dry-run only. Re-run with --apply to restore.' >/dev/null
echo 'PASS: valid backup accepted in dry-run mode'

root="$TMPROOT/asus-edge-test"
printf '%s\n' 'EDGE_TEST_VALUE=2' >"$root/jffs/configs/asus-edge.conf"
tar -czf "$TMPROOT/tampered.tar.gz" -C "$TMPROOT" asus-edge-test
if sh "$ROOT_DIR/scripts/restore.sh" "$TMPROOT/tampered.tar.gz" --dry-run >/dev/null 2>&1; then
    echo 'FAIL: tampered payload unexpectedly accepted' >&2
    exit 1
fi
echo 'PASS: checksum mismatch rejected'

make_valid_backup
printf '%s\n' 'extra' >"$root/jffs/configs/unmanifested.conf"
tar -czf "$TMPROOT/unmanifested.tar.gz" -C "$TMPROOT" asus-edge-test
if sh "$ROOT_DIR/scripts/restore.sh" "$TMPROOT/unmanifested.tar.gz" --dry-run >/dev/null 2>&1; then
    echo 'FAIL: unmanifested payload unexpectedly accepted' >&2
    exit 1
fi
echo 'PASS: unmanifested payload rejected'

make_valid_backup
printf '%s\n' 'not a valid manifest record' >"$root/SHA256SUMS"
tar -czf "$TMPROOT/bad-manifest.tar.gz" -C "$TMPROOT" asus-edge-test
if sh "$ROOT_DIR/scripts/restore.sh" "$TMPROOT/bad-manifest.tar.gz" --dry-run >/dev/null 2>&1; then
    echo 'FAIL: malformed manifest unexpectedly accepted' >&2
    exit 1
fi
echo 'PASS: malformed manifest rejected'
