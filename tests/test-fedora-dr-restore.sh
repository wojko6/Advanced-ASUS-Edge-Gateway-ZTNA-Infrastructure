#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
SCRIPT="$ROOT_DIR/scripts/fedora-dr-restore.sh"
TMPROOT="$(mktemp -d)"
FAKEBIN="$TMPROOT/bin"
TARGET="$TMPROOT/sysroot"
trap 'rm -rf "$TMPROOT"' EXIT HUP INT TERM

mkdir -p "$FAKEBIN" "$TARGET/etc" "$TARGET/boot/grub2" "$TARGET/boot/efi/EFI/fedora"
cat >"$TARGET/etc/fstab" <<'EOF'
UUID=OLD-BOOT-UUID /boot ext4 defaults 0 2
UUID=ROOT-UUID / btrfs subvol=root 0 0
EOF
printf '%s\n' 'search --fs-uuid --set=boot OLD-BOOT-UUID' >"$TARGET/boot/grub2/grub.cfg"
printf '%s\n' 'OLD-BOOT-UUID' >"$TARGET/boot/efi/EFI/fedora/grub.cfg"

cat >"$FAKEBIN/findmnt" <<'EOF'
#!/bin/sh
field=""
path=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        -n) shift ;;
        -o) field="$2"; shift 2 ;;
        -T) path="$2"; shift 2 ;;
        *) shift ;;
    esac
done
case "$field" in
    TARGET)
        if [ "${FAKE_MISSING_BOOT:-0}" = "1" ] && [ "$path" = "$FEDORA_DR_TARGET/boot" ]; then
            printf '%s\n' "$FEDORA_DR_TARGET"
        elif [ "${FAKE_MISSING_EFI:-0}" = "1" ] && [ "$path" = "$FEDORA_DR_TARGET/boot/efi" ]; then
            printf '%s\n' "$FEDORA_DR_TARGET/boot"
        else
            printf '%s\n' "$path"
        fi
        ;;
    SOURCE)
        if [ "$path" = "/" ]; then
            printf '%s\n' /dev/live-root
        elif [ "$path" = "$FEDORA_DR_TARGET" ]; then
            [ "${FAKE_SAME_ROOT:-0}" = "1" ] && printf '%s\n' /dev/live-root || printf '%s\n' /dev/fakeroot
        elif [ "$path" = "$FEDORA_DR_TARGET/boot" ]; then
            printf '%s\n' /dev/fakeboot
        elif [ "$path" = "$FEDORA_DR_TARGET/boot/efi" ]; then
            printf '%s\n' /dev/fakeefi
        fi
        ;;
esac
EOF
cat >"$FAKEBIN/blkid" <<'EOF'
#!/bin/sh
last=""
for arg in "$@"; do last="$arg"; done
[ "$last" = /dev/fakeboot ] && printf '%s\n' NEW-BOOT-UUID
EOF
chmod +x "$FAKEBIN/findmnt" "$FAKEBIN/blkid"

run_dry() {
    FEDORA_DR_TARGET="$TARGET" FEDORA_DR_FINDMNT="$FAKEBIN/findmnt" FEDORA_DR_BLKID="$FAKEBIN/blkid"         sh "$SCRIPT" "$TARGET" --dry-run
}

output="$(run_dry)"
printf '%s\n' "$output" | grep -F 'Detected /boot UUID: NEW-BOOT-UUID' >/dev/null
printf '%s\n' "$output" | grep -F 'update /etc/fstab /boot entry' >/dev/null
printf '%s\n' "$output" | grep -F 'update stale /boot UUID' >/dev/null
printf '%s\n' "$output" | grep -F 'SELinux relabel required' >/dev/null
printf '%s\n' "$output" | grep -F 'Dry-run only' >/dev/null
grep -F 'UUID=OLD-BOOT-UUID /boot' "$TARGET/etc/fstab" >/dev/null
grep -F 'OLD-BOOT-UUID' "$TARGET/boot/grub2/grub.cfg" >/dev/null

if sh "$SCRIPT" / --dry-run >"$TMPROOT/root.out" 2>"$TMPROOT/root.err"; then
    echo "FAIL: running root was accepted as a restore target" >&2
    exit 1
fi
grep -F 'refusing to operate on the running root filesystem' "$TMPROOT/root.err" >/dev/null

for scenario in SAME_ROOT MISSING_BOOT MISSING_EFI; do
    case "$scenario" in
        SAME_ROOT) env_name=FAKE_SAME_ROOT; expected='same filesystem source as the running root' ;;
        MISSING_BOOT) env_name=FAKE_MISSING_BOOT; expected='/boot is not a separate mount' ;;
        MISSING_EFI) env_name=FAKE_MISSING_EFI; expected='/boot/efi is not a separate mount' ;;
    esac
    if env "$env_name=1" FEDORA_DR_TARGET="$TARGET" FEDORA_DR_FINDMNT="$FAKEBIN/findmnt" FEDORA_DR_BLKID="$FAKEBIN/blkid"         sh "$SCRIPT" "$TARGET" --dry-run >"$TMPROOT/$scenario.out" 2>"$TMPROOT/$scenario.err"; then
        echo "FAIL: unsafe target scenario accepted: $scenario" >&2
        exit 1
    fi
    grep -F "$expected" "$TMPROOT/$scenario.err" >/dev/null
done

echo 'PASS: Fedora DR finalization dry-run and target-safety guards'
