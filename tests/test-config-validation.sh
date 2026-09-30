#!/bin/sh

set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

MOCK_IPTABLES_LOG="$TMP_DIR/iptables.log"
MOCK_LOGGER_LOG="$TMP_DIR/logger.log"
export MOCK_IPTABLES_LOG MOCK_LOGGER_LOG

expect_rejected() {
    variable_name="$1"
    invalid_value="$2"
    expected_message="$3"
    config_file="$TMP_DIR/reject-$variable_name.conf"

    cp "$REPO_DIR/config/edge.conf.example" "$config_file"
    printf '%s="%s"\n' "$variable_name" "$invalid_value" >>"$config_file"
    : >"$MOCK_IPTABLES_LOG"
    : >"$MOCK_LOGGER_LOG"

    if EDGE_CONFIG_FILE="$config_file" \
        EDGE_IPTABLES="$TEST_DIR/mocks/iptables" \
        EDGE_IP6TABLES="$TEST_DIR/mocks/ip6tables" \
        EDGE_LOGGER="$TEST_DIR/mocks/logger" \
        sh "$REPO_DIR/router/scripts/firewall-start"; then
        echo "FAIL: invalid $variable_name=$invalid_value was accepted" >&2
        exit 1
    fi

    grep -F "$expected_message" "$MOCK_LOGGER_LOG" >/dev/null || {
        echo "FAIL: rejection was not logged for $variable_name=$invalid_value" >&2
        exit 1
    }

    [ ! -s "$MOCK_IPTABLES_LOG" ] || {
        echo "FAIL: firewall was mutated before rejecting $variable_name=$invalid_value" >&2
        exit 1
    }
}

expect_rejected EDGE_ROUTER_HTTPS_PORT 70000 'invalid port: 70000'
expect_rejected EDGE_ROUTER_HTTPS_TARGET_PORT 70000 'invalid port: 70000'
expect_rejected EDGE_ROUTERCLOUD_PORT 70000 'invalid port: 70000'
expect_rejected EDGE_ROUTERCLOUD_TS_SOURCES '100.64.0.1/99' 'invalid Tailscale source: 100.64.0.1/99'
expect_rejected EDGE_ROUTERCLOUD_IP '192.168.50.999' 'invalid RouterCloud IPv4: 192.168.50.999'

cp "$REPO_DIR/config/edge.conf.example" "$TMP_DIR/printer-edge.conf"
echo 'EDGE_PRINTER_TS_SOURCES="192.0.2.95/32"' >>"$TMP_DIR/printer-edge.conf"
: >"$MOCK_IPTABLES_LOG"
: >"$MOCK_LOGGER_LOG"

if EDGE_CONFIG_FILE="$TMP_DIR/printer-edge.conf" \
    EDGE_IPTABLES="$TEST_DIR/mocks/iptables" \
    EDGE_IP6TABLES="$TEST_DIR/mocks/ip6tables" \
    EDGE_LOGGER="$TEST_DIR/mocks/logger" \
    sh "$REPO_DIR/router/scripts/firewall-start"; then
    echo "FAIL: incomplete printer policy was accepted" >&2
    exit 1
fi

grep -F 'printer sources configured without EDGE_PRINTER_LAN_IP' "$MOCK_LOGGER_LOG" >/dev/null || {
    echo "FAIL: incomplete printer-policy rejection was not logged" >&2
    exit 1
}
[ ! -s "$MOCK_IPTABLES_LOG" ] || {
    echo "FAIL: firewall was mutated before rejecting incomplete printer policy" >&2
    exit 1
}

cp "$REPO_DIR/config/edge.conf.example" "$TMP_DIR/routercloud-collision.conf"
cat >>"$TMP_DIR/routercloud-collision.conf" <<'EOF'
EDGE_ROUTERCLOUD_TS_SOURCES="100.64.0.10/32"
EDGE_ROUTERCLOUD_IP="192.168.50.254"
EDGE_ROUTERCLOUD_PORT="8443"
EOF
: >"$MOCK_IPTABLES_LOG"
: >"$MOCK_LOGGER_LOG"

if EDGE_CONFIG_FILE="$TMP_DIR/routercloud-collision.conf" \
    EDGE_IPTABLES="$TEST_DIR/mocks/iptables" \
    EDGE_IP6TABLES="$TEST_DIR/mocks/ip6tables" \
    EDGE_LOGGER="$TEST_DIR/mocks/logger" \
    sh "$REPO_DIR/router/scripts/firewall-start"; then
    echo "FAIL: router HTTPS / RouterCloud ingress collision was accepted" >&2
    exit 1
fi
grep -F 'router HTTPS ingress port conflicts with RouterCloud port: 8443' "$MOCK_LOGGER_LOG" >/dev/null || {
    echo "FAIL: RouterCloud ingress collision rejection was not logged" >&2
    exit 1
}
[ ! -s "$MOCK_IPTABLES_LOG" ] || {
    echo "FAIL: firewall was mutated before rejecting RouterCloud ingress collision" >&2
    exit 1
}

for flag_name in \
    EDGE_ALLOW_ROUTER_HTTPS \
    EDGE_ALLOW_ROUTER_SSH \
    EDGE_INTERCEPT_DNS \
    EDGE_ENFORCE_LAN_DNS \
    EDGE_BLOCK_LAN_DOT \
    EDGE_ALLOW_LAN_ICMP \
    EDGE_ENABLE_EXIT_NODE \
    EDGE_LOG_DROPS
do
    expect_rejected "$flag_name" 2 "invalid boolean $flag_name: 2"
done

expect_rejected EDGE_TS_IF 'tailscale0;bad' 'invalid Tailscale interface: tailscale0;bad'
expect_rejected EDGE_LAN_IF 'br0 bad' 'invalid LAN interface: br0 bad'
expect_rejected EDGE_WAN_IF 'eth0/1' 'invalid WAN interface: eth0/1'
expect_rejected EDGE_ROUTER_LAN_IP '192.168.50.999' 'invalid router LAN IPv4: 192.168.50.999'
expect_rejected EDGE_TAILNET_V4_CIDR '100.64.0.0/33' 'invalid tailnet IPv4 CIDR: 100.64.0.0/33'
expect_rejected EDGE_ADMIN_TS_SOURCES '100.64.0.1/99' 'invalid Tailscale source: 100.64.0.1/99'
expect_rejected EDGE_PRINTER_TS_SOURCES 'not-an-ip' 'invalid Tailscale source: not-an-ip'
expect_rejected EDGE_ALLOWED_LAN_HOSTS '192.168.50.10/99' 'invalid allowed LAN host: 192.168.50.10/99'
expect_rejected EDGE_PRINTER_LAN_IP '192.168.50.300' 'invalid printer LAN IPv4: 192.168.50.300'

echo "PASS: invalid configuration rejected before firewall mutation"
