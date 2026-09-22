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
: "${EDGE_REQUIRE_USB_PRINTER_DISABLED:=1}"
: "${EDGE_ADVERTISE_ROUTES:=}"
: "${EDGE_ENABLE_EXIT_NODE:=0}"
: "${EDGE_WAN_IF:=}"
: "${EDGE_REQUIRE_SWAP:=auto}"
: "${EDGE_INTERCEPT_DNS:=1}"
: "${EDGE_UNBOUND_PORT:=53535}"
: "${EDGE_UNBOUND_CONFIG:=}"
: "${EDGE_SYSLOG_HOST:=}"
: "${EDGE_SYSLOG_PORT:=6514}"

valid_port() {
    case "$1" in ''|*[!0-9]*) return 1 ;; esac
    [ "$1" -ge 1 ] 2>/dev/null && [ "$1" -le 65535 ] 2>/dev/null
}
valid_boolean() { case "$1" in 0|1) return 0 ;; *) return 1 ;; esac; }
valid_interface() {
    case "$1" in ''|*[!A-Za-z0-9_.:+-]*) return 1 ;; *) [ "${#1}" -le 15 ] ;; esac
}
valid_ipv4() {
    old_ifs="$IFS"; IFS=.; set -- $1; IFS="$old_ifs"
    [ "$#" -eq 4 ] || return 1
    for octet in "$@"; do
        case "$octet" in ''|*[!0-9]*) return 1 ;; esac
        [ "$octet" -le 255 ] 2>/dev/null || return 1
    done
}
valid_ipv4_cidr() {
    case "$1" in */*) address=${1%/*}; prefix=${1#*/} ;; *) return 1 ;; esac
    valid_ipv4 "$address" || return 1
    case "$prefix" in ''|*[!0-9]*) return 1 ;; esac
    [ "$prefix" -le 32 ] 2>/dev/null
}
valid_ipv4_or_cidr() { valid_ipv4 "$1" || valid_ipv4_cidr "$1"; }
valid_host() {
    [ -n "$1" ] || return 1
    [ "${#1}" -le 253 ] || return 1
    case "$1" in
        *[!A-Za-z0-9.-]*|.*|*.|*..*) return 1 ;;
    esac
    old_ifs="$IFS"; IFS=.; set -- $1; IFS="$old_ifs"
    for label in "$@"; do
        [ -n "$label" ] || return 1
        [ "${#label}" -le 63 ] || return 1
        case "$label" in -*|*-) return 1 ;; esac
    done
}

valid_boolean "$EDGE_REQUIRE_USB_PRINTER_DISABLED" || fail "invalid EDGE_REQUIRE_USB_PRINTER_DISABLED value: $EDGE_REQUIRE_USB_PRINTER_DISABLED"
valid_boolean "$EDGE_ENABLE_EXIT_NODE" || fail "invalid EDGE_ENABLE_EXIT_NODE value: $EDGE_ENABLE_EXIT_NODE"
valid_boolean "$EDGE_INTERCEPT_DNS" || fail "invalid EDGE_INTERCEPT_DNS value: $EDGE_INTERCEPT_DNS"
valid_interface "$EDGE_TS_IF" || fail "invalid EDGE_TS_IF value: $EDGE_TS_IF"
valid_interface "$EDGE_LAN_IF" || fail "invalid EDGE_LAN_IF value: $EDGE_LAN_IF"
[ -z "$EDGE_WAN_IF" ] || valid_interface "$EDGE_WAN_IF" || fail "invalid EDGE_WAN_IF value: $EDGE_WAN_IF"
valid_port "$EDGE_UNBOUND_PORT" || fail "invalid EDGE_UNBOUND_PORT value: $EDGE_UNBOUND_PORT"
valid_port "$EDGE_SYSLOG_PORT" || fail "invalid EDGE_SYSLOG_PORT value: $EDGE_SYSLOG_PORT"
[ -z "$EDGE_SYSLOG_HOST" ] || valid_ipv4 "$EDGE_SYSLOG_HOST" || valid_host "$EDGE_SYSLOG_HOST" || fail "invalid EDGE_SYSLOG_HOST value: $EDGE_SYSLOG_HOST"
for source in $EDGE_PRINTER_TS_SOURCES; do valid_ipv4_or_cidr "$source" || fail "invalid printer Tailscale source: $source"; done
[ -z "$EDGE_PRINTER_LAN_IP" ] || valid_ipv4 "$EDGE_PRINTER_LAN_IP" || fail "invalid printer LAN IPv4: $EDGE_PRINTER_LAN_IP"
for port in $EDGE_PRINTER_TCP_PORTS $EDGE_PRINTER_UDP_PORTS; do valid_port "$port" || fail "invalid printer port: $port"; done

case "$EDGE_REQUIRE_SWAP" in
    0|1|auto) ;;
    *) fail "invalid EDGE_REQUIRE_SWAP value: $EDGE_REQUIRE_SWAP" ;;
esac
[ "$EDGE_TS_NETFILTER_MODE" = "off" ] || fail "EDGE_TS_NETFILTER_MODE must be off"

if [ "$FAILURES" -ne 0 ]; then
    printf '\nSummary: %s failure(s), %s warning(s)\n' "$FAILURES" "$WARNINGS"
    exit 1
fi

if opt_is_ready 2>/dev/null; then
    ok "Entware /opt ready"
else
    fail "Entware /opt not ready"
fi
if executable_exists opkg >/dev/null 2>&1; then
    ok "Entware available"
else
    fail "opkg not found"
fi

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

if [ "$tailscale_netfilter_mode" = "0" ]; then
    ok "Tailscale netfilter management disabled"
else
    fail "Tailscale netfilter mode is not off"
fi

native_ts_chains=0
iptables -t filter -S ts-input >/dev/null 2>&1 && native_ts_chains=$((native_ts_chains + 1))
iptables -t filter -S ts-forward >/dev/null 2>&1 && native_ts_chains=$((native_ts_chains + 1))
iptables -t nat -S ts-postrouting >/dev/null 2>&1 && native_ts_chains=$((native_ts_chains + 1))

if [ "$native_ts_chains" -eq 0 ]; then ok "no competing Tailscale netfilter chains"; else fail "competing Tailscale netfilter chains present: $native_ts_chains"; fi


detect_wan_if() {
    [ -n "$EDGE_WAN_IF" ] && { printf '%s\n' "$EDGE_WAN_IF"; return; }

    if executable_exists nvram >/dev/null 2>&1; then
        wan_if="$(nvram get wan0_gw_ifname 2>/dev/null)"
        [ -n "$wan_if" ] || wan_if="$(nvram get wan0_ifname 2>/dev/null)"
        [ -n "$wan_if" ] && {
            valid_interface "$wan_if" || return 1
            printf '%s\n' "$wan_if"
            return
        }
    fi

    wan_if="$(ip route 2>/dev/null | awk '/^default / { print $5; exit }')"
    [ -n "$wan_if" ] && valid_interface "$wan_if" && printf '%s\n' "$wan_if"
}

exit_forward_rule_exists() {
    exit_wan_if="$1"

    iptables -t filter -S EDGE_TS_FORWARD 2>/dev/null |
        awk -v wan="$exit_wan_if" '
            $1 == "-A" && $2 == "EDGE_TS_FORWARD" {
                out=""; target=""
                for (i=3; i<=NF; i++) {
                    if ($i == "-o") out=$(i+1)
                    if ($i == "-j") target=$(i+1)
                }
                if (out == wan && target == "ACCEPT") found=1
            }
            END { exit !found }'
}

platform_wan_nat_exists() {
    exit_wan_if="$1"

    iptables -t nat -S POSTROUTING 2>/dev/null |
        awk -v wan="$exit_wan_if" '
            $1 == "-A" && $2 == "POSTROUTING" {
                out=""; target=""
                for (i=3; i<=NF; i++) {
                    if ($i == "-o") out=$(i+1)
                    if ($i == "-j") target=$(i+1)
                }
                if (out == wan && (target == "MASQUERADE" || target == "SNAT")) found=1
            }
            END { exit !found }'
}

platform_return_path_exists() {
    exit_wan_if="$1"

    iptables -t filter -S FORWARD 2>/dev/null |
        awk -v wan="$exit_wan_if" '
            $1 == "-A" && $2 == "FORWARD" {
                out=""; target=""; states=""
                for (i=3; i<=NF; i++) {
                    if ($i == "-o") out=$(i+1)
                    if ($i == "-j") target=$(i+1)
                    if ($i == "--state" || $i == "--ctstate") states=$(i+1)
                }

                if (!accept_line &&
                    target == "ACCEPT" &&
                    states ~ /ESTABLISHED/ &&
                    states ~ /RELATED/) {
                    accept_line=NR
                }

                if (!drop_line &&
                    target == "DROP" &&
                    (out == "" || out == wan)) {
                    drop_line=NR
                }
            }

            END {
                if (!accept_line) exit 1
                if (drop_line && accept_line > drop_line) exit 1
                exit 0
            }'
}

if [ "$EDGE_ENABLE_EXIT_NODE" = "1" ]; then
    WAN_IF="$(detect_wan_if)" || WAN_IF=""

    if [ -z "$WAN_IF" ]; then
        fail "cannot detect valid WAN interface for exit-node validation"
    else
        ok "exit-node WAN interface resolved: $WAN_IF"

        if [ "$(cat /proc/sys/net/ipv4/ip_forward 2>/dev/null)" = "1" ]; then
            ok "IPv4 forwarding enabled for exit node"
        else
            fail "IPv4 forwarding disabled for exit node"
        fi

        if exit_forward_rule_exists "$WAN_IF"; then
            ok "project exit-node forwarding rule targets $WAN_IF"
        else
            fail "project exit-node forwarding rule missing for $WAN_IF"
        fi

        if platform_wan_nat_exists "$WAN_IF"; then
            ok "platform WAN NAT present for $WAN_IF"
        else
            fail "platform WAN NAT missing for $WAN_IF"
        fi

        if platform_return_path_exists "$WAN_IF"; then
            ok "platform established/related return path present before WAN drop"
        else
            fail "platform established/related return path missing or ordered after WAN drop"
        fi
    fi
fi

if [ "$EDGE_INTERCEPT_DNS" = "1" ]; then
    if grep -F -x "interface=$EDGE_TS_IF" /etc/dnsmasq.conf >/dev/null 2>&1; then ok "dnsmasq includes $EDGE_TS_IF"; else fail "dnsmasq does not include $EDGE_TS_IF"; fi
fi

for chain in EDGE_TS_INPUT EDGE_TS_FORWARD; do
    if iptables -t filter -S "$chain" >/dev/null 2>&1; then ok "firewall chain $chain"; else fail "missing firewall chain $chain"; fi
done
if iptables -t nat -S EDGE_TS_PREROUTING >/dev/null 2>&1; then ok "NAT chain EDGE_TS_PREROUTING"; else fail "missing NAT chain"; fi

check_filter_enforcement() {
    filter_tool="$1"; filter_parent="$2"; filter_chain="$3"
    first_rule="$("$filter_tool" -t filter -S "$filter_parent" 2>/dev/null | awk '$1 == "-A" { print; exit }')"
    if [ "$first_rule" = "-A $filter_parent -i $EDGE_TS_IF -j $filter_chain" ]; then ok "$filter_chain evaluated before other parent rules"; else fail "$filter_chain is not the first parent rule"; fi
    filter_rules="$("$filter_tool" -t filter -S "$filter_chain" 2>/dev/null)"
    last_rule="$(printf '%s\n' "$filter_rules" | awk '$1 == "-A" { last=$0 } END { print last }')"
    if [ "$last_rule" = "-A $filter_chain -j DROP" ]; then ok "$filter_chain ends with unconditional DROP"; else fail "$filter_chain missing terminal DROP"; fi
    if printf '%s\n' "$filter_rules" | grep -F -x -- "-A $filter_chain -j ACCEPT" >/dev/null; then fail "$filter_chain contains unconditional ACCEPT"; fi
}

check_filter_enforcement iptables INPUT EDGE_TS_INPUT
check_filter_enforcement iptables FORWARD EDGE_TS_FORWARD

printer_forward_rule_exists() {
    printer_rule_source="$1"; printer_rule_protocol="$2"; printer_rule_port="$3"
    iptables -t filter -S EDGE_TS_FORWARD 2>/dev/null |
        awk -v input="$EDGE_TS_IF" -v output="$EDGE_LAN_IF" -v source="$printer_rule_source" -v destination="$EDGE_PRINTER_LAN_IP" -v protocol="$printer_rule_protocol" -v port="$printer_rule_port" '
            function host(value) { sub(/\/32$/, "", value); return value }
            { incoming=""; outgoing=""; src=""; dst=""; proto=""; dport=""; target=""; for (i=1; i<NF; i++) { if ($i == "-i") incoming=$(i+1); if ($i == "-o") outgoing=$(i+1); if ($i == "-s") src=$(i+1); if ($i == "-d") dst=$(i+1); if ($i == "-p") proto=$(i+1); if ($i == "--dport") dport=$(i+1); if ($i == "-j") target=$(i+1); if ($i == "!") next } if (incoming == input && outgoing == output && host(src) == host(source) && host(dst) == host(destination) && proto == protocol && dport == port && target == "ACCEPT") found=1 }
            END { exit !found }'
}

if [ -n "$EDGE_PRINTER_TS_SOURCES" ] || [ -n "$EDGE_PRINTER_LAN_IP" ]; then
    if [ -z "$EDGE_PRINTER_TS_SOURCES" ] || [ -z "$EDGE_PRINTER_LAN_IP" ]; then fail "source-scoped printer configuration incomplete"; else
        printer_policy_failures=0
        for source in $EDGE_PRINTER_TS_SOURCES; do
            for port in $EDGE_PRINTER_TCP_PORTS; do if ! printer_forward_rule_exists "$source" tcp "$port"; then fail "missing printer TCP/$port rule for $source"; printer_policy_failures=$((printer_policy_failures + 1)); fi; done
            for port in $EDGE_PRINTER_UDP_PORTS; do if ! printer_forward_rule_exists "$source" udp "$port"; then fail "missing printer UDP/$port rule for $source"; printer_policy_failures=$((printer_policy_failures + 1)); fi; done
        done
        [ "$printer_policy_failures" -eq 0 ] && ok "source-scoped printer policy"
    fi
fi

if [ "$EDGE_REQUIRE_USB_PRINTER_DISABLED" = "1" ]; then
    usb_printer_state="$(nvram get usb_printer 2>/dev/null)"
    if [ "$usb_printer_state" = "0" ]; then ok "ASUS USB print server disabled in NVRAM"; else fail "ASUS USB print server enabled or unknown in NVRAM: ${usb_printer_state:-unset}"; fi
    if pidof lpd >/dev/null 2>&1; then fail "lpd process running"; else ok "lpd process stopped"; fi
    if pidof u2ec >/dev/null 2>&1; then fail "u2ec process running"; else ok "u2ec process stopped"; fi
    if netstat -lnt 2>/dev/null | awk 'NR > 1 { local_addr=$4; if (local_addr ~ /:515$/) found=1 } END { exit !found }'; then fail "router TCP/515 listener present"; else ok "router TCP/515 closed"; fi
fi

if executable_exists ip6tables >/dev/null 2>&1; then
    if ip6tables -t filter -S EDGE_TS6_INPUT >/dev/null 2>&1; then ok "IPv6 INPUT guard"; else fail "missing IPv6 INPUT guard"; fi
    if ip6tables -t filter -S EDGE_TS6_FORWARD >/dev/null 2>&1; then ok "IPv6 FORWARD guard"; else fail "missing IPv6 FORWARD guard"; fi
    check_filter_enforcement ip6tables INPUT EDGE_TS6_INPUT
    check_filter_enforcement ip6tables FORWARD EDGE_TS6_FORWARD
else warn "ip6tables unavailable; verify IPv6 is disabled"; fi

input_jumps="$(iptables -t filter -S INPUT 2>/dev/null | grep -c -- "-i $EDGE_TS_IF -j EDGE_TS_INPUT")"
forward_jumps="$(iptables -t filter -S FORWARD 2>/dev/null | grep -c -- "-i $EDGE_TS_IF -j EDGE_TS_FORWARD")"
prerouting_jumps="$(iptables -t nat -S PREROUTING 2>/dev/null | grep -c -- "-i $EDGE_TS_IF -j EDGE_TS_PREROUTING")"
if [ "$input_jumps" = "1" ]; then ok "single INPUT jump"; else fail "INPUT jump count: $input_jumps"; fi
if [ "$forward_jumps" = "1" ]; then ok "single FORWARD jump"; else fail "FORWARD jump count: $forward_jumps"; fi
if [ "$prerouting_jumps" = "1" ]; then ok "single PREROUTING jump"; else fail "PREROUTING jump count: $prerouting_jumps"; fi

legacy_filter_rules="$({ iptables -t filter -S INPUT 2>/dev/null; iptables -t filter -S FORWARD 2>/dev/null; } | grep -c -- '-i tailscale+.*-j ACCEPT')"
legacy_nat_rules="$(iptables -t nat -S PREROUTING 2>/dev/null | grep -c -- '-i tailscale+')"
if [ "$legacy_filter_rules" = "0" ]; then ok "no legacy broad Tailscale ACCEPT rules"; else fail "legacy broad Tailscale ACCEPT rules: $legacy_filter_rules"; fi
if [ "$legacy_nat_rules" = "0" ]; then ok "no legacy tailscale+ NAT rules"; else fail "legacy tailscale+ NAT rules: $legacy_nat_rules"; fi

if executable_exists ip6tables >/dev/null 2>&1; then
    input6_jumps="$(ip6tables -t filter -S INPUT 2>/dev/null | grep -c -- "-i $EDGE_TS_IF -j EDGE_TS6_INPUT")"
    forward6_jumps="$(ip6tables -t filter -S FORWARD 2>/dev/null | grep -c -- "-i $EDGE_TS_IF -j EDGE_TS6_FORWARD")"
    if [ "$input6_jumps" = "1" ]; then ok "single IPv6 INPUT jump"; else fail "IPv6 INPUT jump count: $input6_jumps"; fi
    if [ "$forward6_jumps" = "1" ]; then ok "single IPv6 FORWARD jump"; else fail "IPv6 FORWARD jump count: $forward6_jumps"; fi
fi

if pidof unbound >/dev/null 2>&1; then ok "Unbound running"; else fail "Unbound not running"; fi
unbound_control_status() {
    if [ -n "$EDGE_UNBOUND_CONFIG" ]; then unbound-control -c "$EDGE_UNBOUND_CONFIG" status >/dev/null 2>&1 && return 0; else
        for candidate in /opt/var/lib/unbound/unbound.conf /opt/etc/unbound/unbound.conf; do [ -f "$candidate" ] && unbound-control -c "$candidate" status >/dev/null 2>&1 && return 0; done
        unbound-control status >/dev/null 2>&1 && return 0
    fi
    return 1
}
if executable_exists unbound-control >/dev/null 2>&1 && unbound_control_status; then ok "Unbound running and control interface reachable"; else fail "Unbound control/status unavailable"; fi
if executable_exists dig >/dev/null 2>&1; then
    if dig +time=3 +tries=1 +dnssec -p "$EDGE_UNBOUND_PORT" @127.0.0.1 cloudflare.com A 2>/dev/null | grep -q 'flags:.* ad'; then ok "Unbound DNSSEC validation on port $EDGE_UNBOUND_PORT (AD flag)"; else warn "DNS resolved without observable AD flag"; fi
else warn "dig not installed; DNSSEC test skipped"; fi
if pidof syslog-ng >/dev/null 2>&1; then ok "syslog-ng running"; else warn "syslog-ng not running"; fi
if [ -n "$EDGE_SYSLOG_HOST" ]; then
    if executable_exists nc >/dev/null 2>&1 && nc -z -w 3 "$EDGE_SYSLOG_HOST" "$EDGE_SYSLOG_PORT" >/dev/null 2>&1; then ok "syslog collector reachable"; else warn "syslog collector not reachable"; fi
fi
printf '\nSummary: %s failure(s), %s warning(s)\n' "$FAILURES" "$WARNINGS"
[ "$FAILURES" -eq 0 ]
