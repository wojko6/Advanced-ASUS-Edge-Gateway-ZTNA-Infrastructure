#!/bin/sh
# Install from a copy of this repository placed on the router.

set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
ADDON_DIR="/jffs/addons/asus-edge"
BACKUP_DIR="$ADDON_DIR/backups/install-$(date +%Y%m%d-%H%M%S)"
APPLY=0

usage() {
    printf '%s\n' "Usage: $0 [--apply]"
    printf '%s\n' "  --apply  run the firewall policy after installation"
}

case "${1:-}" in
    --apply) APPLY=1 ;;
    -h|--help) usage; exit 0 ;;
    '') ;;
    *) usage >&2; exit 2 ;;
esac

[ "$(id -u)" = "0" ] || { echo "ERROR: run as root" >&2; exit 1; }
[ -d /jffs ] || { echo "ERROR: /jffs is unavailable" >&2; exit 1; }
[ -f "$REPO_DIR/config/edge.conf" ] || {
    echo "ERROR: create config/edge.conf from config/edge.conf.example first" >&2
    exit 1
}

for file in "$REPO_DIR/router/scripts/firewall-start" "$REPO_DIR/router/scripts/services-start" "$REPO_DIR/config/edge.conf"; do
    sh -n "$file" || exit 1
done

mkdir -p "$ADDON_DIR/bin" "$ADDON_DIR/legacy" "$BACKUP_DIR" /jffs/scripts /jffs/configs

backup_if_present() {
    [ -e "$1" ] && cp -p "$1" "$BACKUP_DIR/$(basename "$1")"
}

install_file() {
    src="$1"
    dst="$2"
    mode="$3"
    cp "$src" "$dst" || exit 1
    chmod "$mode" "$dst" || exit 1
}

backup_if_present /jffs/configs/asus-edge.conf
backup_if_present /jffs/scripts/firewall-start
backup_if_present /jffs/scripts/services-start

install_file "$REPO_DIR/config/edge.conf" /jffs/configs/asus-edge.conf 0600
install_file "$REPO_DIR/router/scripts/firewall-start" "$ADDON_DIR/bin/firewall-start" 0755
install_file "$REPO_DIR/router/scripts/services-start" "$ADDON_DIR/bin/services-start" 0755
install_file "$REPO_DIR/scripts/healthcheck.sh" "$ADDON_DIR/bin/healthcheck.sh" 0755

install_hook() {
    hook_name="$1"
    hook_path="/jffs/scripts/$hook_name"
    legacy_path="$ADDON_DIR/legacy/$hook_name"

    if [ -f "$hook_path" ] && ! grep -q 'ASUS_EDGE_MANAGED_HOOK' "$hook_path"; then
        cp -p "$hook_path" "$legacy_path" || exit 1
        chmod 0755 "$legacy_path"
    fi

    {
        echo '#!/bin/sh'
        echo '# ASUS_EDGE_MANAGED_HOOK'
        echo "[ -x '$legacy_path' ] && '$legacy_path' \"\$@\""
        echo "exec '$ADDON_DIR/bin/$hook_name' \"\$@\""
    } >"$hook_path" || exit 1
    chmod 0755 "$hook_path"
}

install_hook firewall-start
install_hook services-start

if command -v nvram >/dev/null 2>&1 && [ "$(nvram get jffs2_scripts 2>/dev/null)" != "1" ]; then
    echo "WARNING: enable 'JFFS custom scripts and configs' in Asuswrt-Merlin."
fi

if [ "$APPLY" = "1" ]; then
    echo "Applying Tailscale firewall policy..."
    /jffs/scripts/firewall-start || {
        echo "ERROR: policy failed; restoring hooks from $BACKUP_DIR" >&2
        if [ -f "$BACKUP_DIR/firewall-start" ]; then
            cp -p "$BACKUP_DIR/firewall-start" /jffs/scripts/firewall-start
        else
            rm -f /jffs/scripts/firewall-start
        fi
        command -v service >/dev/null 2>&1 && service restart_firewall >/dev/null 2>&1
        exit 1
    }
fi

echo "Installed Advanced ASUS Edge Gateway v2.0"
echo "Backup: $BACKUP_DIR"
echo "Next: $ADDON_DIR/bin/healthcheck.sh"
