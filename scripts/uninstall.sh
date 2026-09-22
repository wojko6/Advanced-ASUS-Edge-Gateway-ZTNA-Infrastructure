#!/bin/sh

set -u

BASE_PATH="/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin"
if [ -n "${EDGE_TEST_PATH_PREFIX:-}" ]; then
    PATH="${EDGE_TEST_PATH_PREFIX}:${BASE_PATH}"
else
    PATH="$BASE_PATH"
fi
export PATH

# Resolve executables directly because older Asuswrt-Merlin BusyBox shells may
# not implement "command -v". Keep this helper local so each script is standalone.
executable_exists() {
    executable_name="$1"
    case "$executable_name" in
        */*) [ -x "$executable_name" ]; return ;;
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

ROOT_DIR="${EDGE_TEST_ROOT:-}"
JFFS_DIR="${ROOT_DIR}/jffs"
ADDON_DIR="$JFFS_DIR/addons/asus-edge"
CONFIG_FILE="$JFFS_DIR/configs/asus-edge.conf"

uid="$(current_uid)" || { echo "ERROR: cannot determine current user" >&2; exit 1; }
[ "$uid" = "0" ] || { echo "ERROR: run as root" >&2; exit 1; }

if [ -r "$CONFIG_FILE" ]; then
    # shellcheck disable=SC1090
    . "$CONFIG_FILE"
fi
: "${EDGE_TS_IF:=tailscale0}"
: "${EDGE_TS_SOCKET=/var/run/tailscale/tailscaled.sock}"

case "$EDGE_TS_IF" in
    ''|*[!A-Za-z0-9_.:+-]*) echo "ERROR: invalid Tailscale interface" >&2; exit 1 ;;
esac

install_guard() {
    tool="$1"
    parent="$2"
    chain="$3"

    "$tool" -t filter -N "$chain" 2>/dev/null || true
    "$tool" -t filter -F "$chain" || return 1
    "$tool" -t filter -A "$chain" -j DROP || return 1

    while "$tool" -t filter -D "$parent" -i "$EDGE_TS_IF" -j "$chain" 2>/dev/null; do :; done
    "$tool" -t filter -I "$parent" 1 -i "$EDGE_TS_IF" -j "$chain" || return 1
}

remove_guard() {
    tool="$1"
    parent="$2"
    chain="$3"

    while "$tool" -t filter -D "$parent" -i "$EDGE_TS_IF" -j "$chain" 2>/dev/null; do :; done
    "$tool" -t filter -F "$chain" 2>/dev/null || true
    "$tool" -t filter -X "$chain" 2>/dev/null || true
}

remove_jump_and_chain() {
    table="$1"
    parent="$2"
    interface="$3"
    chain="$4"
    while iptables -t "$table" -D "$parent" -i "$interface" -j "$chain" 2>/dev/null; do :; done
    iptables -t "$table" -F "$chain" 2>/dev/null || true
    iptables -t "$table" -X "$chain" 2>/dev/null || true
}

# Fail closed before withdrawing Tailscale advertisements or touching the
# managed EDGE_TS_* chains. If a later step fails, guards intentionally remain.
install_guard iptables INPUT EDGE_UNINSTALL_INPUT_GUARD || {
    echo "ERROR: could not install temporary IPv4 INPUT guard" >&2
    exit 1
}
install_guard iptables FORWARD EDGE_UNINSTALL_FORWARD_GUARD || {
    echo "ERROR: could not install temporary IPv4 FORWARD guard" >&2
    exit 1
}

ipv6_guard_installed=0
if executable_exists ip6tables >/dev/null 2>&1; then
    install_guard ip6tables INPUT EDGE_UNINSTALL6_INPUT_GUARD || {
        echo "ERROR: could not install temporary IPv6 INPUT guard" >&2
        exit 1
    }
    install_guard ip6tables FORWARD EDGE_UNINSTALL6_FORWARD_GUARD || {
        echo "ERROR: could not install temporary IPv6 FORWARD guard" >&2
        exit 1
    }
    ipv6_guard_installed=1
fi

if ! executable_exists tailscale >/dev/null 2>&1; then
    echo "ERROR: tailscale CLI unavailable; guards remain installed and uninstall stopped" >&2
    exit 1
fi
if ! tailscale --socket="$EDGE_TS_SOCKET" down >/dev/null 2>&1; then
    echo "ERROR: could not withdraw Tailscale connectivity; guards remain installed" >&2
    exit 1
fi

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

if [ "$hook_restore_failed" = "1" ]; then
    echo "ERROR: uninstall incomplete; temporary guards remain installed" >&2
    exit 1
fi

if ! executable_exists service >/dev/null 2>&1 || ! service restart_firewall; then
    echo "ERROR: base firewall restart failed; Tailscale is down and temporary guards remain installed" >&2
    exit 1
fi

# A successful firmware firewall rebuild may already have removed these
# temporary chains. Cleanup is therefore best-effort and safe to repeat.
remove_guard iptables INPUT EDGE_UNINSTALL_INPUT_GUARD
remove_guard iptables FORWARD EDGE_UNINSTALL_FORWARD_GUARD
if [ "$ipv6_guard_installed" = "1" ]; then
    remove_guard ip6tables INPUT EDGE_UNINSTALL6_INPUT_GUARD
    remove_guard ip6tables FORWARD EDGE_UNINSTALL6_FORWARD_GUARD
fi

echo "Managed runtime policy removed after fail-closed guard and Tailscale withdrawal."
echo "Previous hooks restored when available; base firewall restarted."
echo "Tailscale remains down intentionally. Re-enable it only after another policy is in place."
echo "Configuration and backups remain under /jffs; remove them manually after verification."
