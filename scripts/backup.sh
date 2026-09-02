#!/bin/sh

set -u

PATH="/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin"
umask 077

current_uid() {
    while read -r status_key status_uid _; do
        if [ "$status_key" = "Uid:" ]; then
            printf '%s\n' "$status_uid"
            return 0
        fi
    done </proc/self/status
    return 1
}

secure_temp_dir() {
    temp_prefix="$1"
    temp_counter=0
    while [ "$temp_counter" -lt 100 ]; do
        temp_candidate="$temp_prefix.$.$temp_counter"
        if (umask 077 && mkdir "$temp_candidate") 2>/dev/null; then
            printf '%s\n' "$temp_candidate"
            return 0
        fi
        temp_counter=$((temp_counter + 1))
    done
    return 1
}

sha256sum_run() {
    for sum_bin in /opt/bin/sha256sum /opt/sbin/sha256sum /usr/bin/sha256sum /usr/sbin/sha256sum /bin/sha256sum /sbin/sha256sum; do
        [ -x "$sum_bin" ] && { "$sum_bin" "$@"; return; }
    done
    if [ -x /bin/busybox ] && /bin/busybox sha256sum /dev/null >/dev/null 2>&1; then
        /bin/busybox sha256sum "$@"
        return
    fi
    echo "ERROR: sha256sum unavailable" >&2
    return 1
}

DESTINATION="${1:-/opt/backups/asus-edge}"
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="$DESTINATION/asus-edge-$STAMP.tar.gz"

uid="$(current_uid)" || { echo "ERROR: cannot determine current user" >&2; exit 1; }
[ "$uid" = "0" ] || { echo "ERROR: run as root" >&2; exit 1; }
mkdir -p "$DESTINATION"
WORK_DIR="$(secure_temp_dir "$DESTINATION/asus-edge-$STAMP")" || {
    echo "ERROR: cannot create private backup workspace" >&2
    exit 1
}
WORK_NAME="$(basename "$WORK_DIR")"
trap 'rm -rf "$WORK_DIR"' EXIT HUP INT TERM
mkdir -p "$WORK_DIR/jffs/scripts" "$WORK_DIR/jffs/configs" \
    "$WORK_DIR/jffs/addons/asus-edge" "$WORK_DIR/jffs/addons/unbound" \
    "$WORK_DIR/opt/etc/unbound" "$WORK_DIR/opt/etc/init.d" \
    "$WORK_DIR/opt/var/lib/unbound"

copy_if_present() {
    src="$1"
    dst="$2"
    [ -e "$src" ] && cp -p "$src" "$dst"
}

copy_if_present /jffs/configs/asus-edge.conf "$WORK_DIR/jffs/configs/"
copy_if_present /jffs/configs/dnsmasq.conf.add "$WORK_DIR/jffs/configs/"
copy_if_present /jffs/scripts/firewall-start "$WORK_DIR/jffs/scripts/"
copy_if_present /jffs/scripts/services-start "$WORK_DIR/jffs/scripts/"
copy_if_present /jffs/scripts/dnsmasq.postconf "$WORK_DIR/jffs/scripts/"
[ -d /jffs/addons/asus-edge/bin ] && cp -R /jffs/addons/asus-edge/bin "$WORK_DIR/jffs/addons/asus-edge/"
[ -d /jffs/addons/asus-edge/legacy ] && cp -R /jffs/addons/asus-edge/legacy "$WORK_DIR/jffs/addons/asus-edge/"
copy_if_present /jffs/addons/unbound/unbound.postconf "$WORK_DIR/jffs/addons/unbound/"
copy_if_present /opt/etc/unbound/unbound.conf "$WORK_DIR/opt/etc/unbound/"
copy_if_present /opt/etc/init.d/S61unbound "$WORK_DIR/opt/etc/init.d/"
copy_if_present /opt/var/lib/unbound/unbound.conf "$WORK_DIR/opt/var/lib/unbound/"
copy_if_present /opt/etc/syslog-ng.conf "$WORK_DIR/opt/etc/"

cat >"$WORK_DIR/README-RESTORE.txt" <<'EOF'
This backup intentionally excludes Tailscale state and authentication material.
Use scripts/restore.sh from the repository. Review the dry-run before --apply.
EOF

(
    cd "$WORK_DIR" || exit 1
    find . -type f ! -name SHA256SUMS | sort | while IFS= read -r file; do
        sha256sum_run "$file" || exit 1
    done >SHA256SUMS
) || exit 1
tar -czf "$ARCHIVE" -C "$DESTINATION" "$WORK_NAME" || exit 1
rm -rf "$WORK_DIR"
trap - EXIT HUP INT TERM
sha256sum_run "$ARCHIVE" >"$ARCHIVE.sha256" || exit 1
chmod 0600 "$ARCHIVE" "$ARCHIVE.sha256"
echo "$ARCHIVE"
