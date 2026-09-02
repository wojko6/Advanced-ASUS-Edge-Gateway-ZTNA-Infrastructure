#!/bin/sh

set -u

DESTINATION="${1:-/opt/backups/asus-edge}"
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="$DESTINATION/asus-edge-$STAMP.tar.gz"

[ "$(id -u)" = "0" ] || { echo "ERROR: run as root" >&2; exit 1; }
mkdir -p "$DESTINATION"
WORK_DIR="$(mktemp -d "$DESTINATION/asus-edge-$STAMP.XXXXXX")" || exit 1
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

(cd "$WORK_DIR" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' \; | sort >SHA256SUMS) || exit 1
tar -czf "$ARCHIVE" -C "$DESTINATION" "$WORK_NAME" || exit 1
rm -rf "$WORK_DIR"
trap - EXIT HUP INT TERM
sha256sum "$ARCHIVE" >"$ARCHIVE.sha256"
chmod 0600 "$ARCHIVE" "$ARCHIVE.sha256"
echo "$ARCHIVE"
