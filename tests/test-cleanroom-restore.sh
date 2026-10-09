#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMPROOT="$(mktemp -d)"
trap 'rm -rf "$TMPROOT"' EXIT HUP INT TERM

PAYLOAD="$TMPROOT/asus-edge-cleanroom"
TARGET="$TMPROOT/target"
mkdir -p "$PAYLOAD/jffs/configs" "$PAYLOAD/jffs/scripts" "$PAYLOAD/opt/etc" "$TARGET"
mkdir -p "$PAYLOAD/jffs/addons/asus-edge/legacy" "$TARGET/jffs/addons/asus-edge"

# Issue #200: archived legacy hooks remain root-private; the other three
# protected trees are outside the CORE payload and must survive restore.
printf '#!/bin/sh\necho legacy\n' >"$PAYLOAD/jffs/addons/asus-edge/legacy/wan-event"
chmod 0700 "$PAYLOAD/jffs/addons/asus-edge/legacy"
chmod 0700 "$PAYLOAD/jffs/addons/asus-edge/legacy/wan-event"
for private_name in backup backups rollback; do
    private_dir="$TARGET/jffs/addons/asus-edge/$private_name"
    mkdir -p "$private_dir"
    chmod 0700 "$private_dir"
    printf 'preserve-%s\n' "$private_name" >"$private_dir/.issue200-marker"
    chmod 0600 "$private_dir/.issue200-marker"
done

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
[ ! -e "$TARGET/jffs/scripts/post-mount" ] || {
    echo "FAIL: review-only post-mount was applied automatically" >&2
    exit 1
}
printf '%s\n' "$output" | grep -F 'post-mount will not be applied automatically' >/dev/null
cmp -s "$PAYLOAD/opt/etc/test.conf" "$TARGET/opt/etc/test.conf"

[ "$(stat -c %a "$TARGET/jffs/configs/asus-edge.conf")" = "600" ]

LEGACY_DIR="$TARGET/jffs/addons/asus-edge/legacy"
test -d "$LEGACY_DIR" && test ! -L "$LEGACY_DIR"
test "$(stat -c %a "$LEGACY_DIR")" = 700
test "$(stat -c %a "$LEGACY_DIR/wan-event")" = 700
cmp -s "$PAYLOAD/jffs/addons/asus-edge/legacy/wan-event" "$LEGACY_DIR/wan-event"
for private_name in backup backups rollback; do
    private_dir="$TARGET/jffs/addons/asus-edge/$private_name"
    test -d "$private_dir" && test ! -L "$private_dir"
    test "$(stat -c %a "$private_dir")" = 700
    test "$(stat -c %a "$private_dir/.issue200-marker")" = 600
    grep -Fxq "preserve-$private_name" "$private_dir/.issue200-marker"
done
echo "PASS: issue #200 legacy restore keeps 0700; other private trees preserved"

if EDGE_RESTORE_ROOT=/ sh "$REPO_DIR/scripts/restore.sh" "$ARCHIVE" --apply >/dev/null 2>&1; then
    echo "FAIL: root alternate restore target unexpectedly accepted" >&2
    exit 1
fi

if EDGE_RESTORE_ROOT=relative/path sh "$REPO_DIR/scripts/restore.sh" "$ARCHIVE" --apply >/dev/null 2>&1; then
    echo "FAIL: relative alternate restore target unexpectedly accepted" >&2
    exit 1
fi

echo "PASS: clean-room alternate-root restore"
