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
ROOT_DIR="${EDGE_TEST_ROOT:-}"
JFFS_DIR="${ROOT_DIR}/jffs"

ADDON_DIR="$JFFS_DIR/addons/asus-edge"
BACKUP_PREFIX="$ADDON_DIR/backups/install-$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR=""
INSTALL_BACKUP_KEEP="${EDGE_INSTALL_BACKUP_KEEP:-3}"
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
[ -d "$JFFS_DIR" ] || { echo "ERROR: $JFFS_DIR is unavailable" >&2; exit 1; }
[ -f "$REPO_DIR/config/edge.conf" ] || {
    echo "ERROR: create config/edge.conf from config/edge.conf.example first" >&2
    exit 1
}

WEBUI_PATCH_BIN="${EDGE_PATCH_BIN:-/opt/bin/patch}"
[ -x "$WEBUI_PATCH_BIN" ] || {
    echo "ERROR: GNU patch is required for the Polish WebUI build: $WEBUI_PATCH_BIN" >&2
    echo "Install it with: opkg install patch" >&2
    exit 1
}

for webui_patch in \
    PL.dict.patch \
    help.js.patch \
    Tools_Sysinfo.asp.patch \
    Tools_OtherSettings.asp.patch \
    Advanced_WAdvanced_Content.asp.patch \
    state.js.patch \
    router_status.asp.patch \
    router.asp.patch \
    internet.asp.patch \
    Advanced_WAN_Content.asp.patch \
    Advanced_BasicFirewall_Content.asp.patch \
    Advanced_Firewall_Content.asp.patch \
    Advanced_FirmwareUpgrade_Content.asp.patch \
    Advanced_System_Content.asp.patch \
    Advanced_SettingBackup_Content.asp.patch \
    Advanced_SNMP_Content.asp.patch \
    Main_LogStatus_Content.asp.patch \
    Main_WStatus_Content.asp.patch \
    Main_DHCPStatus_Content.asp.patch \
    Main_IPV6Status_Content.asp.patch \
    Main_RouteStatus_Content.asp.patch \
    Main_IPTStatus_Content.asp.patch \
    Main_ConnStatus_Content.asp.patch \
    Main_TrafficMonitor_realtime.asp.patch \
    Main_TrafficMonitor_last24.asp.patch \
    Main_TrafficMonitor_daily.asp.patch \
    Main_TrafficMonitor_monthly.asp.patch \
    Main_TrafficMonitor_settings.asp.patch \
    DNSDirector.asp.patch
do
    [ -r "$REPO_DIR/router/webui/patches/$webui_patch" ] || {
        echo "ERROR: missing Polish WebUI patch: $webui_patch" >&2
        exit 1
    }
done

case "$INSTALL_BACKUP_KEEP" in
    ''|*[!0-9]*|0)
        echo "ERROR: EDGE_INSTALL_BACKUP_KEEP must be a positive integer" >&2
        exit 1
        ;;
esac

for file in \
    "$REPO_DIR/router/scripts/firewall-start" \
    "$REPO_DIR/router/scripts/services-start" \
    "$REPO_DIR/router/scripts/dns-guard" \
    "$REPO_DIR/router/scripts/edge-dns-breakglass.sh" \
    "$REPO_DIR/router/scripts/wan-event" \
    "$REPO_DIR/router/scripts/wan-event-handler" \
    "$REPO_DIR/router/scripts/webui-mount" \
    "$REPO_DIR/router/scripts/webui-pl-build" \
    "$REPO_DIR/router/scripts/webui-pl-mount" \
    "$REPO_DIR/router/scripts/webui-status" \
    "$REPO_DIR/scripts/healthcheck.sh" \
    "$REPO_DIR/scripts/check-usb-exposure.sh" \
    "$REPO_DIR/scripts/collect-evidence.sh" \
    "$REPO_DIR/config/edge.conf"
do
    sh -n "$file" || exit 1
done

# Fail closed before creating installer snapshots or touching live files.
# This digest pins the ARMv7 EABI5 soft-float artifact tested for PR #197.
SUPERVISOR_SOURCE="$REPO_DIR/router/bin/edge-dns-supervisor"
SUPERVISOR_SHA256_EXPECTED="26f3615a99448469718f682bde6960e27e30b9466ecfc427c7e392c317103740"

supervisor_sha256() {
    if [ -x /bin/busybox ] &&
       /bin/busybox sha256sum /dev/null >/dev/null 2>&1; then
        /bin/busybox sha256sum "$1"
    elif executable_exists sha256sum; then
        sha256sum "$1"
    else
        return 1
    fi
}

if [ ! -f "$SUPERVISOR_SOURCE" ] ||
   [ -L "$SUPERVISOR_SOURCE" ] ||
   [ ! -s "$SUPERVISOR_SOURCE" ]; then
    echo "ERROR: required ARM supervisor artifact missing, empty or symlink" >&2
    exit 1
fi

supervisor_hash_line="$(supervisor_sha256 "$SUPERVISOR_SOURCE")" || {
    echo "ERROR: cannot calculate ARM supervisor SHA-256" >&2
    exit 1
}
supervisor_sha256_actual="${supervisor_hash_line%% *}"
if [ "$supervisor_sha256_actual" != "$SUPERVISOR_SHA256_EXPECTED" ]; then
    echo "ERROR: supervisor SHA-256 mismatch" >&2
    exit 1
fi
echo "SUPERVISOR_PREFLIGHT=PASS"

umask 077
mkdir -p "$ADDON_DIR/backups"

create_install_backup_dir() {
    backup_counter=0
    while [ "$backup_counter" -lt 100 ]; do
        backup_candidate="$BACKUP_PREFIX-$backup_counter"
        if mkdir "$backup_candidate" 2>/dev/null; then
            BACKUP_DIR="$backup_candidate"
            return 0
        fi
        backup_counter=$((backup_counter + 1))
    done
    return 1
}

create_install_backup_dir || {
    echo "ERROR: cannot create a unique installer rollback snapshot" >&2
    exit 1
}

# Snapshot every path changed by installation, including absent paths on a
# first install. Do not touch live files unless the entire snapshot succeeds.
snapshot_path() {
    if [ -e "$1" ] || [ -L "$1" ]; then
        cp -Rp "$1" "$BACKUP_DIR/$2"
    else
        : >"$BACKUP_DIR/$2.absent"
    fi
}

snapshot_path "$JFFS_DIR/configs/asus-edge.conf" asus-edge.conf
snapshot_path "$JFFS_DIR/scripts/firewall-start" firewall-start
snapshot_path "$JFFS_DIR/scripts/services-start" services-start
snapshot_path "$JFFS_DIR/scripts/wan-event" wan-event
snapshot_path "$JFFS_DIR/scripts/edge-dns-breakglass.sh" edge-dns-breakglass.sh
snapshot_path "$ADDON_DIR/bin" bin
snapshot_path "$ADDON_DIR/legacy" legacy
snapshot_path "$ADDON_DIR/webui" webui

is_managed_install_snapshot() {
    snapshot_name="$(basename "$1")"
    snapshot_rest="${snapshot_name#install-}"
    [ "$snapshot_rest" != "$snapshot_name" ] || return 1

    snapshot_date="${snapshot_rest%%-*}"
    snapshot_rest="${snapshot_rest#*-}"
    [ "${#snapshot_date}" -eq 8 ] || return 1
    case "$snapshot_date" in ''|*[!0-9]*) return 1 ;; esac

    case "$snapshot_rest" in
        *-*)
            snapshot_time="${snapshot_rest%%-*}"
            snapshot_suffix="${snapshot_rest#*-}"
            [ -n "$snapshot_suffix" ] || return 1
            case "$snapshot_suffix" in *[!0-9]*) return 1 ;; esac
            ;;
        *)
            snapshot_time="$snapshot_rest"
            ;;
    esac

    [ "${#snapshot_time}" -eq 6 ] || return 1
    case "$snapshot_time" in ''|*[!0-9]*) return 1 ;; esac
    return 0
}

prune_install_backups() {
    backup_root="$ADDON_DIR/backups"
    backup_count=0

    for snapshot in "$backup_root"/install-*; do
        [ -d "$snapshot" ] || continue
        [ ! -L "$snapshot" ] || continue
        is_managed_install_snapshot "$snapshot" || continue
        backup_count=$((backup_count + 1))
    done

    remove_count=$((backup_count - INSTALL_BACKUP_KEEP))
    [ "$remove_count" -gt 0 ] || return 0

    for snapshot in "$backup_root"/install-*; do
        [ "$remove_count" -gt 0 ] || break
        [ -d "$snapshot" ] || continue
        [ ! -L "$snapshot" ] || continue
        is_managed_install_snapshot "$snapshot" || continue
        [ "$snapshot" != "$BACKUP_DIR" ] || continue
        rm -rf "$snapshot" || return 1
        [ ! -e "$snapshot" ] || return 1
        remove_count=$((remove_count - 1))
    done

    [ "$remove_count" -eq 0 ]
}

prune_install_backups || {
    echo "ERROR: could not enforce installer snapshot retention before live changes" >&2
    exit 1
}

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
        restore_path "$JFFS_DIR/configs/asus-edge.conf" asus-edge.conf || rollback_failed=1
        restore_path "$ADDON_DIR/bin" bin || rollback_failed=1
        restore_path "$ADDON_DIR/legacy" legacy || rollback_failed=1
        restore_path "$ADDON_DIR/webui" webui || rollback_failed=1
        restore_path "$JFFS_DIR/scripts/firewall-start" firewall-start || rollback_failed=1
        restore_path "$JFFS_DIR/scripts/services-start" services-start || rollback_failed=1
        restore_path "$JFFS_DIR/scripts/wan-event" wan-event || rollback_failed=1
        restore_path "$JFFS_DIR/scripts/edge-dns-breakglass.sh" edge-dns-breakglass.sh || rollback_failed=1
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

mkdir -p \
    "$ADDON_DIR/bin" \
    "$ADDON_DIR/legacy" \
    "$ADDON_DIR/webui" \
    "$ADDON_DIR/webui/patches" \
    "$JFFS_DIR/scripts" \
    "$JFFS_DIR/configs"

refuse_symlink_destination() {
    destination="$1"
    if [ -L "$destination" ]; then
        echo "ERROR: refusing to overwrite symlink: $destination" >&2
        exit 1
    fi
}

install_file() {
    src="$1"
    dst="$2"
    mode="$3"
    refuse_symlink_destination "$dst"
    cp "$src" "$dst" || exit 1
    chmod "$mode" "$dst" || exit 1
}

install_file "$REPO_DIR/config/edge.conf" "$JFFS_DIR/configs/asus-edge.conf" 0600
install_file "$REPO_DIR/router/scripts/firewall-start" "$ADDON_DIR/bin/firewall-start" 0755
install_file "$REPO_DIR/router/scripts/services-start" "$ADDON_DIR/bin/services-start" 0755
install_file "$REPO_DIR/router/scripts/dns-guard" "$ADDON_DIR/bin/dns-guard" 0755
install_file "$REPO_DIR/router/bin/edge-dns-supervisor" "$ADDON_DIR/bin/edge-dns-supervisor" 0755
install_file "$REPO_DIR/router/scripts/edge-dns-breakglass.sh" "$JFFS_DIR/scripts/edge-dns-breakglass.sh" 0700
install_file "$REPO_DIR/router/scripts/wan-event" "$ADDON_DIR/bin/wan-event" 0755
install_file "$REPO_DIR/router/scripts/wan-event-handler" "$ADDON_DIR/bin/wan-event-handler" 0755
install_file "$REPO_DIR/router/scripts/webui-mount" "$ADDON_DIR/bin/webui-mount" 0755
install_file "$REPO_DIR/router/scripts/webui-pl-build" "$ADDON_DIR/bin/webui-pl-build" 0755
install_file "$REPO_DIR/router/scripts/webui-pl-mount" "$ADDON_DIR/bin/webui-pl-mount" 0755
install_file "$REPO_DIR/router/scripts/webui-status" "$ADDON_DIR/bin/webui-status" 0755
install_file "$REPO_DIR/router/webui/EdgeGateway.asp" "$ADDON_DIR/webui/EdgeGateway.asp" 0644

for webui_patch in \
    PL.dict.patch \
    help.js.patch \
    Tools_Sysinfo.asp.patch \
    Tools_OtherSettings.asp.patch \
    Advanced_WAdvanced_Content.asp.patch \
    state.js.patch \
    router_status.asp.patch \
    router.asp.patch \
    internet.asp.patch \
    Advanced_WAN_Content.asp.patch \
    Advanced_BasicFirewall_Content.asp.patch \
    Advanced_Firewall_Content.asp.patch \
    Advanced_FirmwareUpgrade_Content.asp.patch \
    Advanced_System_Content.asp.patch \
    Advanced_SettingBackup_Content.asp.patch \
    Advanced_SNMP_Content.asp.patch \
    Main_LogStatus_Content.asp.patch \
    Main_WStatus_Content.asp.patch \
    Main_DHCPStatus_Content.asp.patch \
    Main_IPV6Status_Content.asp.patch \
    Main_RouteStatus_Content.asp.patch \
    Main_IPTStatus_Content.asp.patch \
    Main_ConnStatus_Content.asp.patch \
    Main_TrafficMonitor_realtime.asp.patch \
    Main_TrafficMonitor_last24.asp.patch \
    Main_TrafficMonitor_daily.asp.patch \
    Main_TrafficMonitor_monthly.asp.patch \
    Main_TrafficMonitor_settings.asp.patch \
    DNSDirector.asp.patch
do
    install_file \
        "$REPO_DIR/router/webui/patches/$webui_patch" \
        "$ADDON_DIR/webui/patches/$webui_patch" \
        0644
done

EDGE_ADDON_DIR="$ADDON_DIR" \
EDGE_PATCH_BIN="$WEBUI_PATCH_BIN" \
    "$ADDON_DIR/bin/webui-pl-build" || exit 1
install_file "$REPO_DIR/scripts/healthcheck.sh" "$ADDON_DIR/bin/healthcheck.sh" 0755
install_file "$REPO_DIR/scripts/check-usb-exposure.sh" "$ADDON_DIR/bin/check-usb-exposure.sh" 0755
install_file "$REPO_DIR/scripts/collect-evidence.sh" "$ADDON_DIR/bin/collect-evidence.sh" 0755

install_hook() {
    hook_name="$1"
    hook_path="$JFFS_DIR/scripts/$hook_name"
    legacy_path="$ADDON_DIR/legacy/$hook_name"

    refuse_symlink_destination "$hook_path"

    if [ -f "$hook_path" ] && ! grep -q 'ASUS_EDGE_MANAGED_HOOK' "$hook_path"; then
        cp -p "$hook_path" "$legacy_path" || exit 1
        chmod 0755 "$legacy_path"
    fi

    {
        echo '#!/bin/sh'
        echo '# ASUS_EDGE_MANAGED_HOOK'
        echo "CONFIG_FILE='$JFFS_DIR/configs/asus-edge.conf'"
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
install_hook wan-event

echo "Existing hooks were preserved under $ADDON_DIR/legacy and are disabled by default."
echo "Set EDGE_RUN_LEGACY_HOOKS=1 only after reviewing those files."

if executable_exists nvram >/dev/null 2>&1 && [ "$(nvram get jffs2_scripts 2>/dev/null)" != "1" ]; then
    echo "WARNING: enable 'JFFS custom scripts and configs' in Asuswrt-Merlin."
fi

if [ "$APPLY" = "1" ]; then
    echo "Applying Tailscale firewall policy..."
    firewall_attempted=1
    "$JFFS_DIR/scripts/firewall-start" || exit 1
fi

installation_active=0
RELEASE_VERSION="$(cat "$REPO_DIR/VERSION")"
echo "Installed Advanced ASUS Edge Gateway v$RELEASE_VERSION"
echo "Backup: $BACKUP_DIR"
echo "Next: $ADDON_DIR/bin/healthcheck.sh"
echo "USB exposure check: $ADDON_DIR/bin/check-usb-exposure.sh"
