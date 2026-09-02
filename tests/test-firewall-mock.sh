#!/bin/sh

set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

cp "$REPO_DIR/config/edge.conf.example" "$TMP_DIR/edge.conf"
cat >>"$TMP_DIR/edge.conf" <<'EOF'
EDGE_ADMIN_TS_SOURCES="100.64.0.10/32"
EDGE_ALLOWED_LAN_HOSTS="192.168.50.10"
EDGE_ALLOWED_LAN_TCP_PORTS="443"
EDGE_ALLOWED_LAN_UDP_PORTS="123"
EDGE_ALLOW_LAN_ICMP="1"
EDGE_WAN_IF="eth0"
EOF

chmod +x "$TEST_DIR/mocks/iptables" "$TEST_DIR/mocks/ip6tables" "$TEST_DIR/mocks/logger"
MOCK_IPTABLES_LOG="$TMP_DIR/iptables.log"
export MOCK_IPTABLES_LOG

EDGE_CONFIG_FILE="$TMP_DIR/edge.conf" \
EDGE_IPTABLES="$TEST_DIR/mocks/iptables" \
EDGE_IP6TABLES="$TEST_DIR/mocks/ip6tables" \
EDGE_LOGGER="$TEST_DIR/mocks/logger" \
sh "$REPO_DIR/router/scripts/firewall-start"

assert_rule() {
    grep -F -- "$1" "$MOCK_IPTABLES_LOG" >/dev/null || {
        echo "FAIL: missing rule: $1" >&2
        exit 1
    }
}

assert_rule "-A EDGE_TS_INPUT -s 100.64.0.10/32 -p tcp --dport 8443"
assert_rule "-t nat -A EDGE_TS_PREROUTING -s 100.64.0.10/32 -p tcp --dport 8443 -j DNAT --to-destination 192.168.50.1:8443"
assert_rule "-t filter -D INPUT -i tailscale+ -j ACCEPT"
assert_rule "-t filter -D FORWARD -i tailscale+ -j ACCEPT"
assert_rule "-t nat -D PREROUTING -i tailscale+ -p tcp -m tcp --dport 53 -j DNAT --to-destination 192.168.50.1:53"
assert_rule "-t nat -D PREROUTING -i tailscale+ -p tcp -m tcp --dport 8443 -j DNAT --to-destination 192.168.50.1:8443"
assert_rule "-A EDGE_TS_FORWARD -d 192.168.50.10 -p tcp --dport 443"
assert_rule "-A EDGE_TS_FORWARD -d 192.168.50.10 -p udp --dport 123"
assert_rule "-A EDGE_TS_FORWARD -o eth0 -j ACCEPT"
assert_rule "-A EDGE_TS_FORWARD -j DROP"
assert_rule "-t nat -A EDGE_TS_PREROUTING -p udp --dport 53 -j DNAT"
assert_rule "ip6 -t filter -A EDGE_TS6_INPUT -j DROP"
assert_rule "ip6 -t filter -A EDGE_TS6_FORWARD -j DROP"
assert_rule "ip6 -t filter -I INPUT 1 -i tailscale0 -j DROP"
assert_rule "ip6 -t filter -I FORWARD 1 -i tailscale0 -j DROP"
assert_rule "ip6 -t filter -D INPUT -i tailscale0 -j DROP"
assert_rule "ip6 -t filter -D FORWARD -i tailscale0 -j DROP"

if grep -E -- '-A EDGE_TS_(INPUT|FORWARD) -j ACCEPT$' "$MOCK_IPTABLES_LOG" >/dev/null; then
    echo "FAIL: unrestricted ACCEPT rule found" >&2
    exit 1
fi

echo "PASS: firewall mock policy"
