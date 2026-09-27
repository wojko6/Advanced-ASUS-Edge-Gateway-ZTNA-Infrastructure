#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMPROOT="$(mktemp -d)"
trap 'rm -rf "$TMPROOT"' EXIT HUP INT TERM

PAYLOAD="$TMPROOT/asus-edge-cleanroom"
TARGET="$TMPROOT/target"
mkdir -p "$PAYLOAD/jffs/configs" "$PAYLOAD/jffs/scripts" "$PAYLOAD/opt/etc" "$TARGET"

printf '%s\n' 'EDGE_TEST_VALUE=cleanroom' >"$PAYLOAD/jffs/configs/asus-edge.conf"
printf '%s\n' '#!/bin/sh' '# cleanroom hook' >"$PAYLOAD/jffs/scripts/post-mount"
printf '%s\n' 'test-config' >"$PAYLOAD/opt/etc/test.conf"
chmod 0600 "$PAYLOAD/jffs/configs/asus-edge.conf"
chmod 0755 "$PAYLOAD/jffs/scripts/post-mount"

(
    cd "$PAYLOAD"
    find . -type f ! -name SHA256SUMS | sort | while IFS= read -r file; do
        sha256sum "$file"
    done >SHA256SUMS
)

ARCHIVE="$TMPROOT/backup.tar.gz"
tar -czf "$ARCHIVE" -C "$TMPROOT" "$(basename "$PAYLOAD")"

output="$(
    EDGE_RESTORE_ROOT="$TARGET"     sh "$REPO_DIR/scripts/restore.sh" "$ARCHIVE" --apply
)"
printf '%s\n' "$output" | grep -F "Clean-room restore target: $TARGET" >/dev/null
printf '%s\n' "$output" | grep -F 'Restore completed.' >/dev/null

cmp -s "$PAYLOAD/jffs/configs/asus-edge.conf" "$TARGET/jffs/configs/asus-edge.conf"
cmp -s "$PAYLOAD/jffs/scripts/post-mount" "$TARGET/jffs/scripts/post-mount"
cmp -s "$PAYLOAD/opt/etc/test.conf" "$TARGET/opt/etc/test.conf"

[ "$(stat -c %a "$TARGET/jffs/configs/asus-edge.conf")" = "600" ]
[ "$(stat -c %a "$TARGET/jffs/scripts/post-mount")" = "755" ]

if EDGE_RESTORE_ROOT=/ sh "$REPO_DIR/scripts/restore.sh" "$ARCHIVE" --apply >/dev/null 2>&1; then
    echo "FAIL: root alternate restore target unexpectedly accepted" >&2
    exit 1
fi

if EDGE_RESTORE_ROOT=relative/path sh "$REPO_DIR/scripts/restore.sh" "$ARCHIVE" --apply >/dev/null 2>&1; then
    echo "FAIL: relative alternate restore target unexpectedly accepted" >&2
    exit 1
fi

echo "PASS: clean-room alternate-root restore"
