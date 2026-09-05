#!/bin/sh
# Install from a copy of this repository placed on the router.

set -eu

PATH="/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Resolve executables directly because older Asuswrt-Merlin BusyBox shells may
# not implement "command -v". Keep this helper local so each script is standalone.
executable_exists() {
    executable_name="$1"
    case "$executable_name" in
        */*)
            [ -x "$executable_name" ]
            return
            ;;
    esac

    for executable_dir in /opt/sbin /opt/bin /usr/sbin /usr/bin /sbin /bin; do
        [ -x "$executable_dir/$executable_name" ] && return 0
    done
    return 1
}

current_uid() {
    while read -r status_key status_uid _; do
        if [ "$status_key" = "Uid:" ]; then
            printf '%s\n' "$status_uid"
            return 0
        fi
    done </proc/self/status
    return 1
}

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)"
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

uid="$(current_uid)" || { echo "ERROR: cannot determine current user" >&2; exit 1; }
[ "$uid" = "0" ] || { echo "ERROR: run as root" >&2; exit 1; }
[ -d /jffs ] || { echo "ERROR: /jffs is unavailable" >&2; exit 1; }
[ -f "$REPO_DIR/config/edge.conf" ] || {
    echo "ERROR: create config/edge.conf from config/edge.conf.example first" >&2
    exit 1
}

for file in "$REPO_DIR/router/scripts/firewall-start" "$REPO_DIR/router/scripts/services-start" "$REPO_DIR/config/edge.conf"; do
    sh -n "$file" || exit 1
done

umask 077
mkdir -p "$ADDON_DIR/backups"
mkdir "$BACKUP_DIR" || { echo "ERROR: backup directory already exists or is unavailable" >&2; exit 1; }

# Snapshot every path changed by installation, including absent paths on a
# first install. Do not touch live files unless the entire snapshot succeeds.
snapshot_path() {
    if [ -e "$1" ] || [ -L "$1" ]; then
        cp -Rp "$1" "$BACKUP_DIR/$2"
    else
        : >"$BACKUP_DIR/$2.absent"
    fi
}

snapshot_path /jffs/configs/asus-edge.conf asus-edge.conf
snapshot_path /jffs/scripts/firewall-start firewall-start
snapshot_path /jffs/scripts/services-start services-start
snapshot_path "$ADDON_DIR/bin" bin
snapshot_path "$ADDON_DIR/legacy" legacy

restore_path() {
    # All targets below are fixed project paths, never supplied by the user.
    rm -rf "$1" || return 1
    if [ ! -f "$BACKUP_DIR/$2.absent" ]; then
        cp -Rp "$BACKUP_DIR/$2" "$1" || return 1
    fi
}

installation_active=1
firewall_attempted=0
finish_installation() {
    result=$?
    trap - EXIT HUP INT TERM
    if [ "$installation_active" = "1" ]; then
        echo "ERROR: installation failed; restoring complete snapshot from $BACKUP_DIR" >&2
        rollback_failed=0
        restore_path /jffs/configs/asus-edge.conf asus-edge.conf || rollback_failed=1
        restore_path "$ADDON_DIR/bin" bin || rollback_failed=1
        restore_path "$ADDON_DIR/legacy" legacy || rollback_failed=1
        restore_path /jffs/scripts/firewall-start firewall-start || rollback_failed=1
        restore_path /jffs/scripts/services-start services-start || rollback_failed=1
        if [ "$rollback_failed" = "1" ]; then
            echo "ERROR: rollback incomplete; recover from $BACKUP_DIR using local access" >&2
        elif [ "$firewall_attempted" = "1" ]; then
            if ! executable_exists service || ! service restart_firewall; then
                echo "ERROR: files restored but firewall restart failed; recover using local access" >&2
            fi
        fi
        result=1
    fi
    exit "$result"
}
trap finish_installation EXIT
trap 'exit 1' HUP INT TERM

mkdir -p "$ADDON_DIR/bin" "$ADDON_DIR/legacy" /jffs/scripts /jffs/configs

install_file() {
    src="$1"
    dst="$2"
    mode="$3"
    cp "$src" "$dst" || exit 1
    chmod "$mode" "$dst" || exit 1
}

install_file "$REPO_DIR/config/edge.conf" /jffs/configs/asus-edge.conf 0600
install_file "$REPO_DIR/router/scripts/firewall-start" "$ADDON_DIR/bin/firewall-start" 0755
install_file "$REPO_DIR/router/scripts/services-start" "$ADDON_DIR/bin/services-start" 0755
install_file "$REPO_DIR/scripts/healthcheck.sh" "$ADDON_DIR/bin/healthcheck.sh" 0755
install_file "$REPO_DIR/scripts/check-usb-exposure.sh" "$ADDON_DIR/bin/check-usb-exposure.sh" 0755
install_file "$REPO_DIR/scripts/collect-evidence.sh" "$ADDON_DIR/bin/collect-evidence.sh" 0755

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
        echo "CONFIG_FILE='/jffs/configs/asus-edge.conf'"
        echo '[ -r "$CONFIG_FILE" ] && . "$CONFIG_FILE"'
        echo "if [ \"\${EDGE_RUN_LEGACY_HOOKS:-0}\" = '1' ] && [ -x '$legacy_path' ]; then"
        echo "    '$legacy_path' \"\$@\""
        echo 'fi'
        echo "exec '$ADDON_DIR/bin/$hook_name' \"\$@\""
    } >"$hook_path" || exit 1
    chmod 0755 "$hook_path"
}

install_hook firewall-start
install_hook services-start

echo "Existing hooks were preserved under $ADDON_DIR/legacy and are disabled by default."
echo "Set EDGE_RUN_LEGACY_HOOKS=1 only after reviewing those files."

if executable_exists nvram >/dev/null 2>&1 && [ "$(nvram get jffs2_scripts 2>/dev/null)" != "1" ]; then
    echo "WARNING: enable 'JFFS custom scripts and configs' in Asuswrt-Merlin."
fi

if [ "$APPLY" = "1" ]; then
    echo "Applying Tailscale firewall policy..."
    firewall_attempted=1
    /jffs/scripts/firewall-start || exit 1
fi

installation_active=0
echo "Installed Advanced ASUS Edge Gateway v2.1.1"
echo "Backup: $BACKUP_DIR"
echo "Next: $ADDON_DIR/bin/healthcheck.sh"
echo "USB exposure check: $ADDON_DIR/bin/check-usb-exposure.sh"
