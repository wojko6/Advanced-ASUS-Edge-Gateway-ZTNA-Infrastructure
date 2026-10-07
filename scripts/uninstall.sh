#!/bin/sh

set -u

PATH="/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin"

IPTABLES="${EDGE_IPTABLES:-iptables}"
IP6TABLES="${EDGE_IP6TABLES:-ip6tables}"
ROOT_DIR="${EDGE_TEST_ROOT:-}"
JFFS_DIR="${ROOT_DIR}/jffs"

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

ADDON_DIR="$JFFS_DIR/addons/asus-edge"
DNS_GUARD="${EDGE_DNS_GUARD:-$ADDON_DIR/bin/dns-guard}"
CRU="${EDGE_CRU:-cru}"

uid="$(current_uid)" || { echo "ERROR: cannot determine current user" >&2; exit 1; }
[ "$uid" = "0" ] || { echo "ERROR: run as root" >&2; exit 1; }

remove_jump_and_chain() {
    table="$1"
    parent="$2"
    interface="$3"
    chain="$4"
    while "$IPTABLES" -t "$table" -D "$parent" -i "$interface" -j "$chain" 2>/dev/null; do :; done
    "$IPTABLES" -t "$table" -F "$chain" 2>/dev/null || true
    "$IPTABLES" -t "$table" -X "$chain" 2>/dev/null || true
}

CONFIG_FILE="${EDGE_CONFIG_FILE:-$JFFS_DIR/configs/asus-edge.conf}"
if [ -r "$CONFIG_FILE" ]; then
    # shellcheck disable=SC1090
    . "$CONFIG_FILE"
fi
: "${EDGE_TS_IF:=tailscale0}"
: "${EDGE_LAN_IF:=br0}"

executable_exists "$IPTABLES" >/dev/null 2>&1 || {
    echo "ERROR: iptables not found; refusing incomplete firewall cleanup" >&2
    exit 1
}

dns_guard_watchdog_entry_present() {
    cron_listing="$("$CRU" l 2>/dev/null)" || return 2

    printf '%s\n' "$cron_listing" |
        grep -F '#AsusEdgeDNSGuard#' >/dev/null 2>&1
}

prepare_dns_guard_uninstall() {
    if [ -x "$DNS_GUARD" ]; then
        dns_guard_output="$("$DNS_GUARD" fallback 2>&1)"
        dns_guard_rc=$?

        if [ "$dns_guard_rc" -ne 0 ]; then
            echo "ERROR: DNS Guard could not restore validated WAN bootstrap DNS; refusing uninstall" >&2
            [ -n "$dns_guard_output" ] &&
                printf '%s\n' "$dns_guard_output" >&2
            return 1
        fi

        echo "DNS_UNINSTALL_BOOTSTRAP=PASS"
        return 0
    fi

    if ! executable_exists "$CRU" >/dev/null 2>&1; then
        echo "DNS_UNINSTALL_BOOTSTRAP=LEGACY_NO_GUARD"
        return 0
    fi

    dns_guard_watchdog_entry_present
    watchdog_rc=$?

    case "$watchdog_rc" in
        0)
            echo "ERROR: DNS Guard watchdog exists but DNS Guard binary is unavailable; refusing uninstall" >&2
            return 1
            ;;
        1)
            echo "DNS_UNINSTALL_BOOTSTRAP=LEGACY_NO_GUARD"
            return 0
            ;;
        *)
            echo "ERROR: cannot verify DNS Guard watchdog state; refusing uninstall" >&2
            return 1
            ;;
    esac
}

remove_dns_guard_watchdog() {
    executable_exists "$CRU" >/dev/null 2>&1 || return 0

    cron_listing="$("$CRU" l 2>/dev/null)" || {
        echo "ERROR: cannot list scheduler state before DNS Guard watchdog removal" >&2
        return 1
    }

    printf '%s\n' "$cron_listing" |
        grep -F '#AsusEdgeDNSGuard#' >/dev/null 2>&1 || {
        echo "DNS_GUARD_WATCHDOG=ABSENT"
        return 0
    }

    "$CRU" d AsusEdgeDNSGuard >/dev/null 2>&1 || true

    cron_listing="$("$CRU" l 2>/dev/null)" || {
        echo "ERROR: cannot verify scheduler state after DNS Guard watchdog removal" >&2
        return 1
    }

    if printf '%s\n' "$cron_listing" |
       grep -F '#AsusEdgeDNSGuard#' >/dev/null 2>&1; then
        echo "ERROR: DNS Guard watchdog remains scheduled; refusing firewall cleanup" >&2
        return 1
    fi

    echo "DNS_GUARD_WATCHDOG=REMOVED"
    return 0
}

# Restore a DNS path independent from Pi-hole before disabling the watchdog.
# Complete this before firewall/runtime-hook mutation so failed DNS recovery
# leaves the managed network policy otherwise untouched.
prepare_dns_guard_uninstall || exit 1
remove_dns_guard_watchdog || exit 1

remove_jump_and_chain filter INPUT "$EDGE_TS_IF" EDGE_TS_INPUT
remove_jump_and_chain filter FORWARD "$EDGE_TS_IF" EDGE_TS_FORWARD
remove_jump_and_chain nat PREROUTING "$EDGE_TS_IF" EDGE_TS_PREROUTING
remove_jump_and_chain filter FORWARD "$EDGE_LAN_IF" EDGE_LAN_DOT_FORWARD
remove_jump_and_chain nat PREROUTING "$EDGE_LAN_IF" EDGE_LAN_DNS_PREROUTING


if executable_exists "$IP6TABLES" >/dev/null 2>&1; then
    while "$IP6TABLES" -t filter -D INPUT -i "$EDGE_TS_IF" -j EDGE_TS6_INPUT 2>/dev/null; do :; done
    while "$IP6TABLES" -t filter -D FORWARD -i "$EDGE_TS_IF" -j EDGE_TS6_FORWARD 2>/dev/null; do :; done
    "$IP6TABLES" -t filter -F EDGE_TS6_INPUT 2>/dev/null || true
    "$IP6TABLES" -t filter -F EDGE_TS6_FORWARD 2>/dev/null || true
    "$IP6TABLES" -t filter -X EDGE_TS6_INPUT 2>/dev/null || true
    "$IP6TABLES" -t filter -X EDGE_TS6_FORWARD 2>/dev/null || true
fi

# webui-mount unmount also removes the version-pinned Polish WebUI overlay
# before releasing the Merlin addon page/menu integration.
webui_unmount_failed=0
if [ -x "$ADDON_DIR/bin/webui-mount" ]; then
    if ! "$ADDON_DIR/bin/webui-mount" unmount; then
        echo "ERROR: failed to unmount Edge Gateway WebUI" >&2
        webui_unmount_failed=1
    fi
fi

hook_restore_failed=0
for hook in firewall-start services-start wan-event; do
    current="$JFFS_DIR/scripts/$hook"
    legacy="$ADDON_DIR/legacy/$hook"
    if [ -f "$current" ] && grep -q 'ASUS_EDGE_MANAGED_HOOK' "$current"; then
        if [ -f "$legacy" ]; then
            if ! cp -p "$legacy" "$current"; then
                echo "ERROR: failed to restore previous hook: $hook" >&2
                hook_restore_failed=1
            fi
        elif ! rm -f "$current"; then
            echo "ERROR: failed to remove managed hook: $hook" >&2
            hook_restore_failed=1
        fi
    fi
done

breakglass_path="$JFFS_DIR/scripts/edge-dns-breakglass.sh"
if [ -f "$breakglass_path" ] && grep -q 'ASUS_EDGE_MANAGED_RECOVERY' "$breakglass_path"; then
    rm -f "$breakglass_path" || hook_restore_failed=1
fi

if [ "$hook_restore_failed" = "1" ] || [ "$webui_unmount_failed" = "1" ]; then
    echo "ERROR: uninstall incomplete; inspect /jffs/scripts and WebUI runtime state using local access" >&2
    exit 1
fi

echo "Runtime rules removed and previous hooks restored when available."
echo "Configuration and backups remain under /jffs; remove them manually after verification."
