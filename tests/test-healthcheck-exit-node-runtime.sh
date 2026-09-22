#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

HELPERS="$TMP_DIR/exit-node-health-helpers.sh"
sed -n '/^# BEGIN EXIT_NODE_RUNTIME_HEALTH_HELPERS$/,/^# END EXIT_NODE_RUNTIME_HEALTH_HELPERS$/p' \
    "$REPO_DIR/scripts/healthcheck.sh" >"$HELPERS"

grep -F 'detect_exit_wan_if()' "$HELPERS" >/dev/null || {
    echo "FAIL: exit-node health helper block missing" >&2
    exit 1
}

# shellcheck disable=SC1090
. "$HELPERS"

valid_interface() {
    case "$1" in
        ''|*[!A-Za-z0-9_.:+-]*) return 1 ;;
        *) [ "${#1}" -le 15 ] ;;
    esac
}

executable_exists() {
    [ "$1" = "nvram" ]
}

MOCK_NVRAM_GW_IF=""
MOCK_NVRAM_IF=""
MOCK_DEFAULT_ROUTE_IF=""
MOCK_EDGE_FORWARD=""
MOCK_POSTROUTING=""
MOCK_PARENT_FORWARD=""

nvram() {
    [ "$1" = "get" ] || return 1
    case "$2" in
        wan0_gw_ifname) printf '%s\n' "$MOCK_NVRAM_GW_IF" ;;
        wan0_ifname) printf '%s\n' "$MOCK_NVRAM_IF" ;;
        *) return 1 ;;
    esac
}

ip() {
    [ "$1" = "route" ] || return 1
    [ -n "$MOCK_DEFAULT_ROUTE_IF" ] &&
        printf 'default via 192.0.2.1 dev %s\n' "$MOCK_DEFAULT_ROUTE_IF"
}

iptables() {
    case "$*" in
        "-t filter -S EDGE_TS_FORWARD")
            printf '%s\n' "$MOCK_EDGE_FORWARD"
            ;;
        "-t nat -S POSTROUTING")
            printf '%s\n' "$MOCK_POSTROUTING"
            ;;
        "-t filter -S FORWARD")
            printf '%s\n' "$MOCK_PARENT_FORWARD"
            ;;
        *)
            return 1
            ;;
    esac
}

fail_test() {
    echo "FAIL: $*" >&2
    exit 1
}

EDGE_WAN_IF="ppp0"
export EDGE_WAN_IF
[ "$(detect_exit_wan_if)" = "ppp0" ] ||
    fail_test "configured WAN interface was not preferred"

EDGE_WAN_IF=""
MOCK_NVRAM_GW_IF="ppp0"
MOCK_NVRAM_IF="vlan35"
MOCK_DEFAULT_ROUTE_IF="vlan35"
[ "$(detect_exit_wan_if)" = "ppp0" ] ||
    fail_test "wan0_gw_ifname was not preferred over wan0_ifname/default route"

MOCK_NVRAM_GW_IF=""
MOCK_NVRAM_IF=""
MOCK_DEFAULT_ROUTE_IF="ppp0"
[ "$(detect_exit_wan_if)" = "ppp0" ] ||
    fail_test "default route WAN fallback failed"

MOCK_EDGE_FORWARD='-A EDGE_TS_FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
-A EDGE_TS_FORWARD -o br0 -d 192.168.50.10/32 -p tcp -m tcp --dport 443 -j ACCEPT
-A EDGE_TS_FORWARD -o ppp0 -j ACCEPT
-A EDGE_TS_FORWARD -j DROP'
project_exit_rule_exists ppp0 ||
    fail_test "valid project exit-node forwarding rule was rejected"
if project_exit_rule_exists vlan35; then
    fail_test "wrong-interface project exit-node rule was accepted"
fi

MOCK_POSTROUTING='-P POSTROUTING ACCEPT
-A POSTROUTING -o ppp0 -j PUPNP
-A POSTROUTING ! -s 198.51.100.20/32 -o ppp0 -j MASQUERADE
-A POSTROUTING -o vlan35 -j MASQUERADE'
platform_wan_nat_rule_exists ppp0 ||
    fail_test "platform MASQUERADE on the effective WAN was rejected"
if platform_wan_nat_rule_exists eth0; then
    fail_test "NAT on an unrelated interface was accepted"
fi

MOCK_POSTROUTING='-P POSTROUTING ACCEPT
-A POSTROUTING -o ppp0 -j SNAT --to-source 198.51.100.20'
platform_wan_nat_rule_exists ppp0 ||
    fail_test "platform SNAT on the effective WAN was rejected"

MOCK_POSTROUTING='-P POSTROUTING ACCEPT
-A POSTROUTING -o ppp0 -j PUPNP'
if platform_wan_nat_rule_exists ppp0; then
    fail_test "non-NAT WAN target was accepted as exit-node NAT"
fi

MOCK_PARENT_FORWARD='-P FORWARD ACCEPT
-A FORWARD -i tailscale0 -j EDGE_TS_FORWARD
-A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT
-A FORWARD -j DROP'
platform_return_path_exists ||
    fail_test "state RELATED,ESTABLISHED return path was rejected"

MOCK_PARENT_FORWARD='-P FORWARD ACCEPT
-A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
-A FORWARD -j DROP'
platform_return_path_exists ||
    fail_test "conntrack ESTABLISHED,RELATED return path was rejected"

MOCK_PARENT_FORWARD='-P FORWARD ACCEPT
-A FORWARD -m conntrack --ctstate ESTABLISHED -j ACCEPT
-A FORWARD -j DROP'
if platform_return_path_exists; then
    fail_test "incomplete established-only return path was accepted"
fi

echo "PASS: exit-node healthcheck runtime dependency parsers"
