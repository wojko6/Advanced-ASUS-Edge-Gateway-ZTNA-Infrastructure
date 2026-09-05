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
: "${EDGE_LAN_IF:=br0}"
: "${EDGE_TS_SOCKET:=/var/run/tailscale/tailscaled.sock}"
: "${EDGE_TS_NETFILTER_MODE:=off}"
: "${EDGE_PRINTER_TS_SOURCES:=}"
: "${EDGE_PRINTER_LAN_IP:=}"
: "${EDGE_PRINTER_TCP_PORTS:=80 631 9100}"
: "${EDGE_PRINTER_UDP_PORTS:=161}"
: "${EDGE_ADVERTISE_ROUTES:=}"
: "${EDGE_ENABLE_EXIT_NODE:=0}"
: "${EDGE_REQUIRE_SWAP:=auto}"
: "${EDGE_INTERCEPT_DNS:=1}"
: "${EDGE_UNBOUND_PORT:=53535}"
: "${EDGE_UNBOUND_CONFIG:=}"
: "${EDGE_SYSLOG_HOST:=}"
: "${EDGE_SYSLOG_PORT:=6514}"

opt_is_ready 2>/dev/null && ok "Entware /opt ready" || fail "Entware /opt not ready"
executable_exists opkg >/dev/null 2>&1 && ok "Entware available" || fail "opkg not found"

swap_required=0
case "$EDGE_REQUIRE_SWAP" in
    1) swap_required=1 ;;
    0) ;;
    auto)
        if [ "$(cat /proc/sys/vm/overcommit_memory 2>/dev/null)" = "2" ]; then
            case "$(uname -m 2>/dev/null)" in
                armv[5-8]*|i[3-6]86|mips*|ppc) swap_required=1 ;;
            esac
        fi
        ;;
    *) fail "invalid EDGE_REQUIRE_SWAP value: $EDGE_REQUIRE_SWAP" ;;
esac

if [ "$swap_required" = "1" ]; then
    if awk 'NR > 1 { found=1 } END { exit !found }' /proc/swaps 2>/dev/null; then
        ok "required swap active"
    else
        fail "required swap inactive"
    fi
fi

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

tailscale_netfilter_mode="$(
    tailscale --socket="$EDGE_TS_SOCKET" debug prefs 2>/dev/null |
        awk -F: '/"NetfilterMode"/ {
            value=$2
            gsub(/[[:space:],]/, "", value)
            print value
            exit
        }'
)"

if [ "$EDGE_TS_NETFILTER_MODE" != "off" ]; then
    fail "EDGE_TS_NETFILTER_MODE must be off"
elif [ "$tailscale_netfilter_mode" = "0" ]; then
    ok "Tailscale netfilter management disabled"
else
    fail "Tailscale netfilter mode is not off"
fi

native_ts_chains=0
iptables -t filter -S ts-input >/dev/null 2>&1 &&
    native_ts_chains=$((native_ts_chains + 1))
iptables -t filter -S ts-forward >/dev/null 2>&1 &&
    native_ts_chains=$((native_ts_chains + 1))
iptables -t nat -S ts-postrouting >/dev/null 2>&1 &&
    native_ts_chains=$((native_ts_chains + 1))

if [ "$native_ts_chains" -eq 0 ]; then
    ok "no competing Tailscale netfilter chains"
else
    fail "competing Tailscale netfilter chains present: $native_ts_chains"
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

check_filter_enforcement() {
    filter_tool="$1"
    filter_parent="$2"
    filter_chain="$3"
    first_rule="$("$filter_tool" -t filter -S "$filter_parent" 2>/dev/null |
        awk '$1 == "-A" { print; exit }')"
    if [ "$first_rule" = "-A $filter_parent -i $EDGE_TS_IF -j $filter_chain" ]; then
        ok "$filter_chain evaluated before other parent rules"
    else
        fail "$filter_chain is not the first parent rule"
    fi
    filter_rules="$("$filter_tool" -t filter -S "$filter_chain" 2>/dev/null)"
    last_rule="$(printf '%s\n' "$filter_rules" | awk '$1 == "-A" { last=$0 } END { print last }')"
    if [ "$last_rule" = "-A $filter_chain -j DROP" ]; then
        ok "$filter_chain ends with unconditional DROP"
    else
        fail "$filter_chain missing terminal DROP"
    fi
    if printf '%s\n' "$filter_rules" | grep -F -x -- "-A $filter_chain -j ACCEPT" >/dev/null; then
        fail "$filter_chain contains unconditional ACCEPT"
    fi
}

check_filter_enforcement iptables INPUT EDGE_TS_INPUT
check_filter_enforcement iptables FORWARD EDGE_TS_FORWARD

printer_forward_rule_exists() {
    printer_rule_source="$1"
    printer_rule_protocol="$2"
    printer_rule_port="$3"

    iptables -t filter -S EDGE_TS_FORWARD 2>/dev/null |
        awk -v input="$EDGE_TS_IF" -v output="$EDGE_LAN_IF" \
            -v source="$printer_rule_source" -v destination="$EDGE_PRINTER_LAN_IP" \
            -v protocol="$printer_rule_protocol" -v port="$printer_rule_port" '
            function host(value) { sub(/\/32$/, "", value); return value }
            {
                incoming=""; outgoing=""; src=""; dst=""; proto=""; dport=""; target=""
                for (i=1; i<NF; i++) {
                    if ($i == "-i") incoming=$(i+1)
                    if ($i == "-o") outgoing=$(i+1)
                    if ($i == "-s") src=$(i+1)
                    if ($i == "-d") dst=$(i+1)
                    if ($i == "-p") proto=$(i+1)
                    if ($i == "--dport") dport=$(i+1)
                    if ($i == "-j") target=$(i+1)
                    if ($i == "!") next
                }
                if (incoming == input && outgoing == output && host(src) == host(source) &&
                    host(dst) == host(destination) && proto == protocol && dport == port &&
                    target == "ACCEPT") found=1
            }
            END { exit !found }
        '
}

if [ -n "$EDGE_PRINTER_TS_SOURCES" ] || [ -n "$EDGE_PRINTER_LAN_IP" ]; then
    if [ -z "$EDGE_PRINTER_TS_SOURCES" ] || [ -z "$EDGE_PRINTER_LAN_IP" ]; then
        fail "source-scoped printer configuration incomplete"
    else
        printer_policy_failures=0
        for source in $EDGE_PRINTER_TS_SOURCES; do
            for port in $EDGE_PRINTER_TCP_PORTS; do
                if ! printer_forward_rule_exists "$source" tcp "$port"; then
                    fail "missing printer TCP/$port rule for $source"
                    printer_policy_failures=$((printer_policy_failures + 1))
                fi
            done
            for port in $EDGE_PRINTER_UDP_PORTS; do
                if ! printer_forward_rule_exists "$source" udp "$port"; then
                    fail "missing printer UDP/$port rule for $source"
                    printer_policy_failures=$((printer_policy_failures + 1))
                fi
            done
        done
        [ "$printer_policy_failures" -eq 0 ] && ok "source-scoped printer policy"
    fi
fi

if executable_exists ip6tables >/dev/null 2>&1; then
    ip6tables -t filter -S EDGE_TS6_INPUT >/dev/null 2>&1 && ok "IPv6 INPUT guard" || fail "missing IPv6 INPUT guard"
    ip6tables -t filter -S EDGE_TS6_FORWARD >/dev/null 2>&1 && ok "IPv6 FORWARD guard" || fail "missing IPv6 FORWARD guard"
    check_filter_enforcement ip6tables INPUT EDGE_TS6_INPUT
    check_filter_enforcement ip6tables FORWARD EDGE_TS6_FORWARD
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
