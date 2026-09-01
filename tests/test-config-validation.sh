#!/bin/sh

set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

cp "$REPO_DIR/config/edge.conf.example" "$TMP_DIR/edge.conf"
echo 'EDGE_ROUTER_HTTPS_PORT="70000"' >>"$TMP_DIR/edge.conf"

MOCK_IPTABLES_LOG="$TMP_DIR/iptables.log"
MOCK_LOGGER_LOG="$TMP_DIR/logger.log"
export MOCK_IPTABLES_LOG MOCK_LOGGER_LOG

if EDGE_CONFIG_FILE="$TMP_DIR/edge.conf" \
    EDGE_IPTABLES="$TEST_DIR/mocks/iptables" \
    EDGE_IP6TABLES="$TEST_DIR/mocks/ip6tables" \
    EDGE_LOGGER="$TEST_DIR/mocks/logger" \
    sh "$REPO_DIR/router/scripts/firewall-start"; then
    echo "FAIL: invalid port was accepted" >&2
    exit 1
fi

grep -F 'invalid port: 70000' "$MOCK_LOGGER_LOG" >/dev/null || {
    echo "FAIL: invalid-port rejection was not logged" >&2
    exit 1
}

echo "PASS: invalid configuration rejected"
