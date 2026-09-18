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
printf '%s\n' /dev/fakeboot
EOF
cat >"$FAKEBIN/blkid" <<'EOF'
#!/bin/sh
printf '%s\n' NEW-BOOT-UUID
EOF
chmod +x "$FAKEBIN/findmnt" "$FAKEBIN/blkid"

output="$(
    PATH="$FAKEBIN:/usr/sbin:/usr/bin:/sbin:/bin"     FEDORA_DR_PATH="$FAKEBIN:/usr/sbin:/usr/bin:/sbin:/bin"     "$SCRIPT" "$TARGET" --dry-run
)"

printf '%s\n' "$output" | grep -F 'Detected /boot UUID: NEW-BOOT-UUID' >/dev/null
printf '%s\n' "$output" | grep -F 'update /etc/fstab /boot entry' >/dev/null
printf '%s\n' "$output" | grep -F 'update stale /boot UUID' >/dev/null
printf '%s\n' "$output" | grep -F 'SELinux relabel required' >/dev/null
printf '%s\n' "$output" | grep -F 'Dry-run only' >/dev/null

grep -F 'UUID=OLD-BOOT-UUID /boot' "$TARGET/etc/fstab" >/dev/null
grep -F 'OLD-BOOT-UUID' "$TARGET/boot/grub2/grub.cfg" >/dev/null

echo 'PASS: Fedora DR restore dry-run detects UUID and SELinux remediation without changing target'
