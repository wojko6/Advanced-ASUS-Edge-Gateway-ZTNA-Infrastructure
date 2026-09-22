#!/bin/sh
set -eu
TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

expect_rejected() {
    name="$1"; value="$2"; expected="$3"
    cfg="$TMP_DIR/$name.conf"
    cp "$REPO_DIR/config/edge.conf.example" "$cfg"
    printf '%s="%s"\n' "$name" "$value" >>"$cfg"
    output="$TMP_DIR/$name.out"
    if EDGE_CONFIG_FILE="$cfg" sh "$REPO_DIR/scripts/healthcheck.sh" >"$output" 2>&1; then
        echo "FAIL: healthcheck accepted $name=$value" >&2
        exit 1
    fi
    grep -F "$expected" "$output" >/dev/null || {
        echo "FAIL: expected rejection missing for $name=$value" >&2
        cat "$output" >&2
        exit 1
    }
}

expect_rejected EDGE_REQUIRE_USB_PRINTER_DISABLED 2 'invalid EDGE_REQUIRE_USB_PRINTER_DISABLED value: 2'
expect_rejected EDGE_ENABLE_EXIT_NODE yes 'invalid EDGE_ENABLE_EXIT_NODE value: yes'
expect_rejected EDGE_INTERCEPT_DNS maybe 'invalid EDGE_INTERCEPT_DNS value: maybe'
expect_rejected EDGE_ENFORCE_LAN_DNS maybe 'invalid EDGE_ENFORCE_LAN_DNS value: maybe'
expect_rejected EDGE_BLOCK_LAN_DOT maybe 'invalid EDGE_BLOCK_LAN_DOT value: maybe'
expect_rejected EDGE_DOT_PORT 70000 'invalid EDGE_DOT_PORT value: 70000'
expect_rejected EDGE_ROUTER_LAN_IP '192.168.50.999' 'invalid EDGE_ROUTER_LAN_IP value: 192.168.50.999'
expect_rejected EDGE_DNS_PORT 70000 'invalid EDGE_DNS_PORT value: 70000'
expect_rejected EDGE_TS_IF 'tailscale0;bad' 'invalid EDGE_TS_IF value: tailscale0;bad'
expect_rejected EDGE_LAN_IF 'br0 bad' 'invalid EDGE_LAN_IF value: br0 bad'
expect_rejected EDGE_WAN_IF 'ppp0;bad' 'invalid EDGE_WAN_IF value: ppp0;bad'
expect_rejected EDGE_UNBOUND_PORT 70000 'invalid EDGE_UNBOUND_PORT value: 70000'
expect_rejected EDGE_SYSLOG_PORT abc 'invalid EDGE_SYSLOG_PORT value: abc'
expect_rejected EDGE_SYSLOG_HOST 'collector;reboot' 'invalid EDGE_SYSLOG_HOST value: collector;reboot'
expect_rejected EDGE_SYSLOG_HOST '.collector.example' 'invalid EDGE_SYSLOG_HOST value: .collector.example'
expect_rejected EDGE_PRINTER_TS_SOURCES '100.64.0.1/99' 'invalid printer Tailscale source: 100.64.0.1/99'
expect_rejected EDGE_PRINTER_LAN_IP '192.168.50.300' 'invalid printer LAN IPv4: 192.168.50.300'
expect_rejected EDGE_PRINTER_TCP_PORTS 0 'invalid printer port: 0'
expect_rejected EDGE_REQUIRE_SWAP invalid 'invalid EDGE_REQUIRE_SWAP value: invalid'
expect_rejected EDGE_TS_NETFILTER_MODE on 'EDGE_TS_NETFILTER_MODE must be off'

echo 'PASS: healthcheck rejects invalid configuration before runtime checks'
