#!/bin/sh

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

CONFIG_FILE="${EDGE_CONFIG_FILE:-/jffs/configs/asus-edge.conf}"
FAILURES=0
WARNINGS=0

ok() { printf '[OK]   %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*"; WARNINGS=$((WARNINGS + 1)); }
fail() { printf '[FAIL] %s\n' "$*"; FAILURES=$((FAILURES + 1)); }

opt_is_ready() {
    [ -d /opt ] || return 1
    [ -x /opt/bin/opkg ] || [ -x /opt/sbin/opkg ]
}

if [ -r "$CONFIG_FILE" ]; then
    # shellcheck disable=SC1090
    . "$CONFIG_FILE"
    ok "configuration readable"
else
    fail "configuration missing: $CONFIG_FILE"
fi

: "${EDGE_TS_IF:=tailscale0}"
: "${EDGE_TS_SOCKET:=/var/run/tailscale/tailscaled.sock}"
: "${EDGE_ADVERTISE_ROUTES:=}"
: "${EDGE_ENABLE_EXIT_NODE:=0}"
: "${EDGE_INTERCEPT_DNS:=1}"
: "${EDGE_UNBOUND_PORT:=53535}"
: "${EDGE_UNBOUND_CONFIG:=}"
: "${EDGE_SYSLOG_HOST:=}"
: "${EDGE_SYSLOG_PORT:=6514}"

opt_is_ready 2>/dev/null && ok "Entware /opt ready" || fail "Entware /opt not ready"
executable_exists opkg >/dev/null 2>&1 && ok "Entware available" || fail "opkg not found"

if pidof tailscaled >/dev/null 2>&1; then
    ok "tailscaled running"
else
    fail "tailscaled not running"
fi

if tailscale --socket="$EDGE_TS_SOCKET" status >/dev/null 2>&1; then
    ok "Tailscale connected"
else
    fail "Tailscale not connected"
fi

if ip link show "$EDGE_TS_IF" >/dev/null 2>&1; then
    ok "$EDGE_TS_IF exists"
else
    fail "$EDGE_TS_IF missing"
fi

if [ "$EDGE_INTERCEPT_DNS" = "1" ]; then
    if grep -F -x "interface=$EDGE_TS_IF" /etc/dnsmasq.conf >/dev/null 2>&1; then
        ok "dnsmasq includes $EDGE_TS_IF"
    else
        fail "dnsmasq does not include $EDGE_TS_IF"
    fi
fi

for chain in EDGE_TS_INPUT EDGE_TS_FORWARD; do
    iptables -t filter -S "$chain" >/dev/null 2>&1 && ok "firewall chain $chain" || fail "missing firewall chain $chain"
done
iptables -t nat -S EDGE_TS_PREROUTING >/dev/null 2>&1 && ok "NAT chain EDGE_TS_PREROUTING" || fail "missing NAT chain"

if executable_exists ip6tables >/dev/null 2>&1; then
    ip6tables -t filter -S EDGE_TS6_INPUT >/dev/null 2>&1 && ok "IPv6 INPUT guard" || fail "missing IPv6 INPUT guard"
    ip6tables -t filter -S EDGE_TS6_FORWARD >/dev/null 2>&1 && ok "IPv6 FORWARD guard" || fail "missing IPv6 FORWARD guard"
else
    warn "ip6tables unavailable; verify IPv6 is disabled"
fi

input_jumps="$(iptables -t filter -S INPUT 2>/dev/null | grep -c -- "-i $EDGE_TS_IF -j EDGE_TS_INPUT")"
forward_jumps="$(iptables -t filter -S FORWARD 2>/dev/null | grep -c -- "-i $EDGE_TS_IF -j EDGE_TS_FORWARD")"
prerouting_jumps="$(iptables -t nat -S PREROUTING 2>/dev/null | grep -c -- "-i $EDGE_TS_IF -j EDGE_TS_PREROUTING")"
[ "$input_jumps" = "1" ] && ok "single INPUT jump" || fail "INPUT jump count: $input_jumps"
[ "$forward_jumps" = "1" ] && ok "single FORWARD jump" || fail "FORWARD jump count: $forward_jumps"
[ "$prerouting_jumps" = "1" ] && ok "single PREROUTING jump" || fail "PREROUTING jump count: $prerouting_jumps"

legacy_filter_rules="$({
    iptables -t filter -S INPUT 2>/dev/null
    iptables -t filter -S FORWARD 2>/dev/null
} | grep -c -- '-i tailscale+.*-j ACCEPT')"
legacy_nat_rules="$(iptables -t nat -S PREROUTING 2>/dev/null | grep -c -- '-i tailscale+')"
[ "$legacy_filter_rules" = "0" ] && ok "no legacy broad Tailscale ACCEPT rules" || fail "legacy broad Tailscale ACCEPT rules: $legacy_filter_rules"
[ "$legacy_nat_rules" = "0" ] && ok "no legacy tailscale+ NAT rules" || fail "legacy tailscale+ NAT rules: $legacy_nat_rules"

if executable_exists ip6tables >/dev/null 2>&1; then
    input6_jumps="$(ip6tables -t filter -S INPUT 2>/dev/null | grep -c -- "-i $EDGE_TS_IF -j EDGE_TS6_INPUT")"
    forward6_jumps="$(ip6tables -t filter -S FORWARD 2>/dev/null | grep -c -- "-i $EDGE_TS_IF -j EDGE_TS6_FORWARD")"
    [ "$input6_jumps" = "1" ] && ok "single IPv6 INPUT jump" || fail "IPv6 INPUT jump count: $input6_jumps"
    [ "$forward6_jumps" = "1" ] && ok "single IPv6 FORWARD jump" || fail "IPv6 FORWARD jump count: $forward6_jumps"
fi

unbound_control_status() {
    if [ -n "$EDGE_UNBOUND_CONFIG" ]; then
        [ -r "$EDGE_UNBOUND_CONFIG" ] || return 1
        unbound-control -c "$EDGE_UNBOUND_CONFIG" status >/dev/null 2>&1
        return
    fi

    for unbound_config in /opt/var/lib/unbound/unbound.conf /opt/etc/unbound/unbound.conf; do
        [ -r "$unbound_config" ] || continue
        if unbound-control -c "$unbound_config" status >/dev/null 2>&1; then
            return 0
        fi
    done
    return 1
}

if executable_exists unbound-control >/dev/null 2>&1 && unbound_control_status; then
    ok "Unbound running and control interface reachable"
else
    fail "Unbound control/status unavailable"
fi

if executable_exists dig >/dev/null 2>&1; then
    if dig +time=3 +tries=1 +dnssec -p "$EDGE_UNBOUND_PORT" @127.0.0.1 cloudflare.com A 2>/dev/null | grep -q 'flags:.* ad'; then
        ok "Unbound DNSSEC validation on port $EDGE_UNBOUND_PORT (AD flag)"
    else
        warn "DNS resolved without observable AD flag"
    fi
else
    warn "dig not installed; DNSSEC test skipped"
fi

pidof syslog-ng >/dev/null 2>&1 && ok "syslog-ng running" || warn "syslog-ng not running"

if [ -n "$EDGE_SYSLOG_HOST" ]; then
    if executable_exists nc >/dev/null 2>&1 && nc -z -w 3 "$EDGE_SYSLOG_HOST" "$EDGE_SYSLOG_PORT" >/dev/null 2>&1; then
        ok "syslog collector reachable"
    else
        warn "syslog collector not reachable"
    fi
fi

printf '\nSummary: %s failure(s), %s warning(s)\n' "$FAILURES" "$WARNINGS"
[ "$FAILURES" -eq 0 ]
