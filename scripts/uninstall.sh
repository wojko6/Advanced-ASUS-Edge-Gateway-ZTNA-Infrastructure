#!/bin/sh

set -u

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

ADDON_DIR="/jffs/addons/asus-edge"

uid="$(current_uid)" || { echo "ERROR: cannot determine current user" >&2; exit 1; }
[ "$uid" = "0" ] || { echo "ERROR: run as root" >&2; exit 1; }

remove_jump_and_chain() {
    table="$1"
    parent="$2"
    interface="$3"
    chain="$4"
    while iptables -t "$table" -D "$parent" -i "$interface" -j "$chain" 2>/dev/null; do :; done
    iptables -t "$table" -F "$chain" 2>/dev/null || true
    iptables -t "$table" -X "$chain" 2>/dev/null || true
}

CONFIG_FILE="/jffs/configs/asus-edge.conf"
if [ -r "$CONFIG_FILE" ]; then
    # shellcheck disable=SC1090
    . "$CONFIG_FILE"
fi
: "${EDGE_TS_IF:=tailscale0}"

remove_jump_and_chain filter INPUT "$EDGE_TS_IF" EDGE_TS_INPUT
remove_jump_and_chain filter FORWARD "$EDGE_TS_IF" EDGE_TS_FORWARD
remove_jump_and_chain nat PREROUTING "$EDGE_TS_IF" EDGE_TS_PREROUTING

if executable_exists ip6tables >/dev/null 2>&1; then
    while ip6tables -t filter -D INPUT -i "$EDGE_TS_IF" -j EDGE_TS6_INPUT 2>/dev/null; do :; done
    while ip6tables -t filter -D FORWARD -i "$EDGE_TS_IF" -j EDGE_TS6_FORWARD 2>/dev/null; do :; done
    ip6tables -t filter -F EDGE_TS6_INPUT 2>/dev/null || true
    ip6tables -t filter -F EDGE_TS6_FORWARD 2>/dev/null || true
    ip6tables -t filter -X EDGE_TS6_INPUT 2>/dev/null || true
    ip6tables -t filter -X EDGE_TS6_FORWARD 2>/dev/null || true
fi

for hook in firewall-start services-start; do
    current="/jffs/scripts/$hook"
    legacy="$ADDON_DIR/legacy/$hook"
    if [ -f "$current" ] && grep -q 'ASUS_EDGE_MANAGED_HOOK' "$current"; then
        if [ -f "$legacy" ]; then
            cp -p "$legacy" "$current"
        else
            rm -f "$current"
        fi
    fi
done

echo "Runtime rules removed and previous hooks restored when available."
echo "Configuration and backups remain under /jffs; remove them manually after verification."
