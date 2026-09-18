#!/bin/sh
#
# Fedora clean-room restore finalization helper.
#
# Run from a Fedora Live/rescue environment after the restored target filesystem
# is mounted at TARGET_ROOT. The target must NOT be the running host.
#
# Usage:
#   sudo ./scripts/fedora-dr-restore.sh /mnt/sysroot --dry-run
#   sudo ./scripts/fedora-dr-restore.sh /mnt/sysroot --apply
#
set -eu

PATH="/usr/sbin:/usr/bin:/sbin:/bin"
FINDMNT_BIN="${FEDORA_DR_FINDMNT:-findmnt}"
BLKID_BIN="${FEDORA_DR_BLKID:-blkid}"

TARGET_ROOT="${1:-}"
MODE="${2:---dry-run}"

usage() {
    echo "Usage: $0 TARGET_ROOT [--dry-run|--apply]" >&2
}

[ -n "$TARGET_ROOT" ] || { usage; exit 2; }
[ -d "$TARGET_ROOT/etc" ] || { echo "ERROR: target is not a mounted Fedora root: $TARGET_ROOT" >&2; exit 1; }
[ -f "$TARGET_ROOT/etc/fstab" ] || { echo "ERROR: target has no /etc/fstab: $TARGET_ROOT" >&2; exit 1; }
case "$MODE" in
    --dry-run|--apply) ;;
    *) usage; exit 2 ;;
esac

findmnt_cmd() {
    $FINDMNT_BIN -no "$1" -T "$2"
}

boot_source="$(findmnt_cmd SOURCE "$TARGET_ROOT/boot" 2>/dev/null || true)"
[ -n "$boot_source" ] || {
    echo "ERROR: /boot is not mounted in the target layout." >&2
    echo "Mount the restored /boot filesystem first." >&2
    exit 1
}

case "$boot_source" in
    /dev/*)
        boot_uuid="$($BLKID_BIN -s UUID -o value "$boot_source" 2>/dev/null || true)"
        ;;
    UUID=*)
        boot_uuid="${boot_source#UUID=}"
        ;;
    *)
        boot_uuid=""
        ;;
esac

[ -n "$boot_uuid" ] || {
    echo "ERROR: cannot determine UUID of the restored /boot filesystem." >&2
    echo "Detected /boot source: $boot_source" >&2
    exit 1
}

current_boot_spec="$(awk '
    $0 !~ /^[[:space:]]*#/ && NF >= 2 && $2 == "/boot" { print $1; exit }
' "$TARGET_ROOT/etc/fstab")"

[ -n "$current_boot_spec" ] || {
    echo "ERROR: no /boot entry found in target /etc/fstab." >&2
    exit 1
}

old_boot_uuid=""
case "$current_boot_spec" in
    UUID=*) old_boot_uuid="${current_boot_spec#UUID=}" ;;
esac

echo "Target: $TARGET_ROOT"
echo "Detected /boot source: $boot_source"
echo "Detected /boot UUID: $boot_uuid"
echo "Current fstab /boot spec: $current_boot_spec"

if [ "$current_boot_spec" = "UUID=$boot_uuid" ]; then
    echo "PASS: /etc/fstab already references the current /boot UUID."
else
    echo "ACTION: update /etc/fstab /boot entry to UUID=$boot_uuid"
fi

changed_files="$TARGET_ROOT/etc/fstab"
grub_candidates="
$TARGET_ROOT/boot/grub2/grub.cfg
$TARGET_ROOT/boot/efi/EFI/fedora/grub.cfg
"

for candidate in $grub_candidates; do
    [ -f "$candidate" ] || continue
    case "$candidate" in
        "$TARGET_ROOT/boot/grub2/grub.cfg"|"$TARGET_ROOT/boot/efi/EFI/fedora/grub.cfg")
            ;;
        *) continue ;;
    esac
    if [ -n "$old_boot_uuid" ] && grep -Fq "$old_boot_uuid" "$candidate"; then
        echo "ACTION: update stale /boot UUID in $candidate"
        changed_files="$changed_files
$candidate"
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

timestamp="$(date +%Y%m%d-%H%M%S)"
backup_dir="/var/tmp/fedora-dr-restore-$timestamp"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"

rollback() {
    echo "ERROR: restore finalization failed; restoring changed configuration files." >&2
    failed=0
    if [ -f "$backup_dir/fstab" ]; then
        cp -p "$backup_dir/fstab" "$TARGET_ROOT/etc/fstab" || failed=1
    fi
    if [ -f "$backup_dir/grub.cfg" ]; then
        cp -p "$backup_dir/grub.cfg" "$TARGET_ROOT/boot/grub2/grub.cfg" || failed=1
    fi
    if [ -f "$backup_dir/efi-grub.cfg" ]; then
        cp -p "$backup_dir/efi-grub.cfg" "$TARGET_ROOT/boot/efi/EFI/fedora/grub.cfg" || failed=1
    fi
    if [ "$failed" -ne 0 ]; then
        echo "ERROR: rollback was incomplete; inspect $backup_dir" >&2
        exit 1
    fi
    echo "Rollback completed; backups retained at $backup_dir" >&2
    exit 1
}

cp -p "$TARGET_ROOT/etc/fstab" "$backup_dir/fstab" || rollback

[ "$current_boot_spec" = "UUID=$boot_uuid" ] || {
    awk -v uuid="$boot_uuid" '
        $0 !~ /^[[:space:]]*#/ && NF >= 2 && $2 == "/boot" {
            $1 = "UUID=" uuid
        }
        { print }
    ' "$backup_dir/fstab" >"$TARGET_ROOT/etc/fstab.new" || rollback
    mv "$TARGET_ROOT/etc/fstab.new" "$TARGET_ROOT/etc/fstab" || rollback
}

if [ -f "$TARGET_ROOT/boot/grub2/grub.cfg" ]; then
    cp -p "$TARGET_ROOT/boot/grub2/grub.cfg" "$backup_dir/grub.cfg" || rollback
fi
if [ -f "$TARGET_ROOT/boot/efi/EFI/fedora/grub.cfg" ]; then
    cp -p "$TARGET_ROOT/boot/efi/EFI/fedora/grub.cfg" "$backup_dir/efi-grub.cfg" || rollback
fi

if [ -n "$old_boot_uuid" ] && [ "$old_boot_uuid" != "$boot_uuid" ]; then
    for candidate in "$TARGET_ROOT/boot/grub2/grub.cfg" "$TARGET_ROOT/boot/efi/EFI/fedora/grub.cfg"; do
        [ -f "$candidate" ] || continue
        if grep -Fq "$old_boot_uuid" "$candidate"; then
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
echo "PASS: /boot UUID and SELinux labeling are aligned with the restored target."
echo "Recovery backups retained at: $backup_dir"
