#!/bin/sh
#
# Fedora clean-room restore finalization helper.
#
# This is NOT a full bare-metal restore engine. Run it from Fedora Live/rescue
# only after the recovered root, /boot and /boot/efi filesystems are mounted
# below TARGET_ROOT.
#
# Usage:
#   sudo sh ./scripts/fedora-dr-restore.sh /mnt/sysroot --dry-run
#   sudo sh ./scripts/fedora-dr-restore.sh /mnt/sysroot --apply
#
set -eu

PATH="/usr/sbin:/usr/bin:/sbin:/bin"
FINDMNT_BIN="${FEDORA_DR_FINDMNT:-findmnt}"
BLKID_BIN="${FEDORA_DR_BLKID:-blkid}"

TARGET_ROOT_INPUT="${1:-}"
MODE="${2:---dry-run}"

usage() {
    echo "Usage: $0 TARGET_ROOT [--dry-run|--apply]" >&2
}

[ -n "$TARGET_ROOT_INPUT" ] || { usage; exit 2; }
case "$MODE" in
    --dry-run|--apply) ;;
    *) usage; exit 2 ;;
esac

TARGET_ROOT="$(CDPATH='' cd -- "$TARGET_ROOT_INPUT" 2>/dev/null && pwd -P)" || {
    echo "ERROR: target root does not exist or cannot be resolved: $TARGET_ROOT_INPUT" >&2
    exit 1
}

[ "$TARGET_ROOT" != "/" ] || {
    echo "ERROR: refusing to operate on the running root filesystem (/)." >&2
    exit 1
}
[ -d "$TARGET_ROOT/etc" ] || {
    echo "ERROR: target is not a mounted Fedora root: $TARGET_ROOT" >&2
    exit 1
}
[ -f "$TARGET_ROOT/etc/fstab" ] || {
    echo "ERROR: target has no /etc/fstab: $TARGET_ROOT" >&2
    exit 1
}

findmnt_value() {
    "$FINDMNT_BIN" -n -o "$1" -T "$2"
}

require_exact_mount() {
    mount_path="$1"
    mount_label="$2"
    actual_target="$(findmnt_value TARGET "$mount_path" 2>/dev/null || true)"
    if [ "$actual_target" != "$mount_path" ]; then
        echo "ERROR: $mount_label is not a separate mount at $mount_path." >&2
        echo "Detected containing mount: ${actual_target:-none}" >&2
        exit 1
    fi
}

require_exact_mount "$TARGET_ROOT" "target root"

running_root_source="$(findmnt_value SOURCE / 2>/dev/null || true)"
target_root_source="$(findmnt_value SOURCE "$TARGET_ROOT" 2>/dev/null || true)"
[ -n "$running_root_source" ] && [ -n "$target_root_source" ] || {
    echo "ERROR: cannot determine running/target root filesystem source." >&2
    exit 1
}
[ "$running_root_source" != "$target_root_source" ] || {
    echo "ERROR: target root resolves to the same filesystem source as the running root; refusing." >&2
    exit 1
}

require_exact_mount "$TARGET_ROOT/boot" "/boot"
require_exact_mount "$TARGET_ROOT/boot/efi" "/boot/efi"

boot_source="$(findmnt_value SOURCE "$TARGET_ROOT/boot" 2>/dev/null || true)"
efi_source="$(findmnt_value SOURCE "$TARGET_ROOT/boot/efi" 2>/dev/null || true)"
[ -n "$boot_source" ] || { echo "ERROR: cannot determine restored /boot source." >&2; exit 1; }
[ -n "$efi_source" ] || { echo "ERROR: cannot determine restored /boot/efi source." >&2; exit 1; }
[ "$boot_source" != "$target_root_source" ] || {
    echo "ERROR: /boot resolves to the target root filesystem instead of a separate mount." >&2
    exit 1
}
[ "$efi_source" != "$boot_source" ] || {
    echo "ERROR: /boot/efi resolves to the same filesystem as /boot." >&2
    exit 1
}

case "$boot_source" in
    /dev/*) boot_uuid="$("$BLKID_BIN" -s UUID -o value "$boot_source" 2>/dev/null || true)" ;;
    UUID=*) boot_uuid="${boot_source#UUID=}" ;;
    *) boot_uuid="" ;;
esac

[ -n "$boot_uuid" ] || {
    echo "ERROR: cannot determine UUID of the restored /boot filesystem." >&2
    echo "Detected /boot source: $boot_source" >&2
    exit 1
}

current_boot_spec="$(awk '
    $0 !~ /^[[:space:]]*#/ && NF >= 2 && $2 == "/boot" { print $1; exit }
' "$TARGET_ROOT/etc/fstab")"

[ -n "$current_boot_spec" ] || { echo "ERROR: no /boot entry found in target /etc/fstab." >&2; exit 1; }

case "$current_boot_spec" in
    UUID=*) old_boot_uuid="${current_boot_spec#UUID=}" ;;
    *) echo "ERROR: unsupported /boot fstab source '$current_boot_spec'; expected UUID=..." >&2; exit 1 ;;
esac

echo "Target: $TARGET_ROOT"
echo "Target root source: $target_root_source"
echo "Detected /boot source: $boot_source"
echo "Detected /boot UUID: $boot_uuid"
echo "Detected /boot/efi source: $efi_source"
echo "Current fstab /boot spec: $current_boot_spec"

if [ "$current_boot_spec" = "UUID=$boot_uuid" ]; then
    echo "PASS: /etc/fstab already references the current /boot UUID."
else
    echo "ACTION: update /etc/fstab /boot entry to UUID=$boot_uuid"
fi

grub_candidates="
$TARGET_ROOT/boot/grub2/grub.cfg
$TARGET_ROOT/boot/efi/EFI/fedora/grub.cfg
"

for candidate in $grub_candidates; do
    [ -f "$candidate" ] || continue
    case "$candidate" in
        "$TARGET_ROOT/boot/grub2/grub.cfg"|"$TARGET_ROOT/boot/efi/EFI/fedora/grub.cfg") ;;
        *) continue ;;
    esac
    if grep -Fq "$old_boot_uuid" "$candidate"; then
        echo "ACTION: update stale /boot UUID in $candidate"
    else
        echo "CHECK: no stale old /boot UUID found in $candidate"
    fi
done

echo "CHECK: SELinux relabel required for restored /boot: restorecon -RF /boot"

[ "$MODE" = "--dry-run" ] && {
    echo "Dry-run only. Re-run with --apply to make the recovery-target fixes."
    exit 0
}

uid="$(id -u)"
[ "$uid" = "0" ] || { echo "ERROR: --apply must run as root." >&2; exit 1; }

umask 077
backup_dir="$(mktemp -d /var/tmp/fedora-dr-restore.XXXXXX)" || {
    echo "ERROR: cannot create private rollback directory under /var/tmp." >&2
    exit 1
}
chmod 700 "$backup_dir"

rollback() {
    echo "ERROR: restore finalization failed; restoring changed configuration files." >&2
    failed=0
    [ ! -f "$backup_dir/fstab" ] || cp -p "$backup_dir/fstab" "$TARGET_ROOT/etc/fstab" || failed=1
    [ ! -f "$backup_dir/grub.cfg" ] || cp -p "$backup_dir/grub.cfg" "$TARGET_ROOT/boot/grub2/grub.cfg" || failed=1
    [ ! -f "$backup_dir/efi-grub.cfg" ] || cp -p "$backup_dir/efi-grub.cfg" "$TARGET_ROOT/boot/efi/EFI/fedora/grub.cfg" || failed=1
    if [ "$failed" -ne 0 ]; then
        echo "ERROR: rollback was incomplete; inspect $backup_dir" >&2
        exit 1
    fi
    echo "Rollback completed; backups retained at $backup_dir" >&2
    exit 1
}

cp -p "$TARGET_ROOT/etc/fstab" "$backup_dir/fstab" || rollback

if [ "$current_boot_spec" != "UUID=$boot_uuid" ]; then
    cp -p "$backup_dir/fstab" "$TARGET_ROOT/etc/fstab.new" || rollback
    awk -v uuid="$boot_uuid" '
        $0 !~ /^[[:space:]]*#/ && NF >= 2 && $2 == "/boot" { $1 = "UUID=" uuid }
        { print }
    ' "$backup_dir/fstab" >"$TARGET_ROOT/etc/fstab.new" || rollback
    mv "$TARGET_ROOT/etc/fstab.new" "$TARGET_ROOT/etc/fstab" || rollback
fi

[ ! -f "$TARGET_ROOT/boot/grub2/grub.cfg" ] || cp -p "$TARGET_ROOT/boot/grub2/grub.cfg" "$backup_dir/grub.cfg" || rollback
[ ! -f "$TARGET_ROOT/boot/efi/EFI/fedora/grub.cfg" ] || cp -p "$TARGET_ROOT/boot/efi/EFI/fedora/grub.cfg" "$backup_dir/efi-grub.cfg" || rollback

if [ "$old_boot_uuid" != "$boot_uuid" ]; then
    for candidate in "$TARGET_ROOT/boot/grub2/grub.cfg" "$TARGET_ROOT/boot/efi/EFI/fedora/grub.cfg"; do
        [ -f "$candidate" ] || continue
        if grep -Fq "$old_boot_uuid" "$candidate"; then
            cp -p "$candidate" "$candidate.new" || rollback
            sed "s/$old_boot_uuid/$boot_uuid/g" "$candidate" >"$candidate.new" || rollback
            mv "$candidate.new" "$candidate" || rollback
        fi
    done
fi

[ -x "$TARGET_ROOT/sbin/restorecon" ] || {
    echo "ERROR: target /sbin/restorecon is missing; refusing to claim SELinux relabel success." >&2
    rollback
}
chroot "$TARGET_ROOT" /sbin/restorecon -RF /boot || rollback

echo "PASS: Fedora restore finalization completed."
echo "PASS: /boot UUID references and SELinux labeling are aligned with the restored target."
echo "Recovery configuration backups retained at: $backup_dir"
