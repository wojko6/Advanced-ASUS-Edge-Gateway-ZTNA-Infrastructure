#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
HANDLER="$ROOT_DIR/router/scripts/wan-event-handler"

TMPDIR_TEST="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_TEST"' EXIT HUP INT TERM

MOCK_BIN="$TMPDIR_TEST/bin"
mkdir -p "$MOCK_BIN"

CONFIG="$TMPDIR_TEST/asus-edge.conf"
RESOLV="$TMPDIR_TEST/resolv.conf"
TAILSCALED_INIT="$TMPDIR_TEST/S06tailscaled"
LOGFILE="$TMPDIR_TEST/logger.log"
INIT_LOG="$TMPDIR_TEST/tailscaled-init.log"

printf '%s\n' \
    'EDGE_UNBOUND_PORT=53535' \
    "EDGE_TS_SOCKET=\"$TMPDIR_TEST/tailscaled.sock\"" \
    'EDGE_WAN_DNS_WAIT_SECONDS=1' \
    'EDGE_TAILSCALE_WAIT_SECONDS=1' \
    > "$CONFIG"

printf '%s\n' 'nameserver 8.8.8.8' > "$RESOLV"

printf '%s\n' \
    '#!/bin/sh' \
    'case "$1" in' \
    '  dnsmasq|unbound|tailscaled) echo 1234; exit 0 ;;' \
    'esac' \
    'exit 1' \
    > "$MOCK_BIN/pidof"

printf '%s\n' \
    '#!/bin/sh' \
    'echo "tcp 0 0 127.0.0.1:53535 0.0.0.0:* LISTEN"' \
    > "$MOCK_BIN/netstat"

printf '%s\n' \
    '#!/bin/sh' \
    'exit 0' \
    > "$MOCK_BIN/tailscale"

printf '%s\n' \
    '#!/bin/sh' \
    "printf '%s\n' \"\$*\" >> \"$LOGFILE\"" \
    > "$MOCK_BIN/logger"

printf '%s\n' \
    '#!/bin/sh' \
    'exit 0' \
    > "$MOCK_BIN/sleep"

printf '%s\n' \
    '#!/bin/sh' \
    "printf '%s\n' \"\$*\" >> \"$INIT_LOG\"" \
    'exit 0' \
    > "$TAILSCALED_INIT"

chmod +x \
    "$MOCK_BIN/pidof" \
    "$MOCK_BIN/netstat" \
    "$MOCK_BIN/tailscale" \
    "$MOCK_BIN/logger" \
    "$MOCK_BIN/sleep" \
    "$TAILSCALED_INIT"

EDGE_CONFIG_FILE="$CONFIG" \
EDGE_RESOLV_CONF="$RESOLV" \
EDGE_TAILSCALED_INIT="$TAILSCALED_INIT" \
EDGE_TEST_PATH_PREFIX="$MOCK_BIN" \
"$HANDLER"

grep -qx 'nameserver 127.0.0.1' "$RESOLV"
grep -qx 'restart' "$INIT_LOG"

echo "PASS: wan-event-handler mock test"

echo "=== TEST: DNS path unavailable ==="

TMPDIR_FAIL="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_TEST" "$TMPDIR_FAIL"' EXIT HUP INT TERM

MOCK_BIN_FAIL="$TMPDIR_FAIL/bin"
mkdir -p "$MOCK_BIN_FAIL"

CONFIG_FAIL="$TMPDIR_FAIL/asus-edge.conf"
RESOLV_FAIL="$TMPDIR_FAIL/resolv.conf"
TAILSCALED_INIT_FAIL="$TMPDIR_FAIL/S06tailscaled"
LOGFILE_FAIL="$TMPDIR_FAIL/logger.log"
INIT_LOG_FAIL="$TMPDIR_FAIL/tailscaled-init.log"

printf '%s\n' \
    'EDGE_UNBOUND_PORT=53535' \
    'EDGE_WAN_DNS_WAIT_SECONDS=1' \
    'EDGE_TAILSCALE_WAIT_SECONDS=1' \
    > "$CONFIG_FAIL"

printf '%s\n' 'nameserver 8.8.8.8' > "$RESOLV_FAIL"

printf '%s\n' \
    '#!/bin/sh' \
    'exit 1' \
    > "$MOCK_BIN_FAIL/pidof"

printf '%s\n' \
    '#!/bin/sh' \
    'exit 0' \
    > "$MOCK_BIN_FAIL/netstat"

printf '%s\n' \
    '#!/bin/sh' \
    'exit 0' \
    > "$MOCK_BIN_FAIL/tailscale"

printf '%s\n' \
    '#!/bin/sh' \
    "printf '%s\n' \"\$*\" >> \"$LOGFILE_FAIL\"" \
    > "$MOCK_BIN_FAIL/logger"

printf '%s\n' \
    '#!/bin/sh' \
    'exit 0' \
    > "$MOCK_BIN_FAIL/sleep"

printf '%s\n' \
    '#!/bin/sh' \
    "printf '%s\n' \"\$*\" >> \"$INIT_LOG_FAIL\"" \
    'exit 0' \
    > "$TAILSCALED_INIT_FAIL"

chmod +x \
    "$MOCK_BIN_FAIL/pidof" \
    "$MOCK_BIN_FAIL/netstat" \
    "$MOCK_BIN_FAIL/tailscale" \
    "$MOCK_BIN_FAIL/logger" \
    "$MOCK_BIN_FAIL/sleep" \
    "$TAILSCALED_INIT_FAIL"

if EDGE_CONFIG_FILE="$CONFIG_FAIL" \
   EDGE_RESOLV_CONF="$RESOLV_FAIL" \
   EDGE_TAILSCALED_INIT="$TAILSCALED_INIT_FAIL" \
   EDGE_TEST_PATH_PREFIX="$MOCK_BIN_FAIL" \
   "$HANDLER"
then
    echo "FAIL: handler succeeded although DNS path was unavailable"
    exit 1
fi

grep -q 'local DNS path not ready' "$LOGFILE_FAIL"

if [ -s "$INIT_LOG_FAIL" ]; then
    echo "FAIL: tailscaled restart was attempted"
    exit 1
fi

echo "PASS: DNS unavailable is handled correctly"

echo "=== TEST: resolv.conf missing ==="

TMPDIR_RESOLV="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_TEST" "$TMPDIR_FAIL" "$TMPDIR_RESOLV"' EXIT HUP INT TERM

MOCK_BIN_RESOLV="$TMPDIR_RESOLV/bin"
mkdir -p "$MOCK_BIN_RESOLV"

CONFIG_RESOLV="$TMPDIR_RESOLV/asus-edge.conf"
RESOLV_MISSING="$TMPDIR_RESOLV/resolv.conf"
TAILSCALED_INIT_RESOLV="$TMPDIR_RESOLV/S06tailscaled"
LOGFILE_RESOLV="$TMPDIR_RESOLV/logger.log"
INIT_LOG_RESOLV="$TMPDIR_RESOLV/tailscaled-init.log"

printf '%s\n' \
    'EDGE_UNBOUND_PORT=53535' \
    'EDGE_WAN_DNS_WAIT_SECONDS=1' \
    'EDGE_TAILSCALE_WAIT_SECONDS=1' \
    > "$CONFIG_RESOLV"

printf '%s\n' \
    '#!/bin/sh' \
    'case "$1" in' \
    '  dnsmasq|unbound|tailscaled) echo 1234; exit 0 ;;' \
    'esac' \
    'exit 1' \
    > "$MOCK_BIN_RESOLV/pidof"

printf '%s\n' \
    '#!/bin/sh' \
    'echo "tcp 0 0 127.0.0.1:53535 0.0.0.0:* LISTEN"' \
    > "$MOCK_BIN_RESOLV/netstat"

printf '%s\n' \
    '#!/bin/sh' \
    'exit 0' \
    > "$MOCK_BIN_RESOLV/tailscale"

printf '%s\n' \
    '#!/bin/sh' \
    "printf '%s\n' \"\$*\" >> \"$LOGFILE_RESOLV\"" \
    > "$MOCK_BIN_RESOLV/logger"

printf '%s\n' \
    '#!/bin/sh' \
    'exit 0' \
    > "$MOCK_BIN_RESOLV/sleep"

printf '%s\n' \
    '#!/bin/sh' \
    "printf '%s\n' \"\$*\" >> \"$INIT_LOG_RESOLV\"" \
    'exit 0' \
    > "$TAILSCALED_INIT_RESOLV"

chmod +x \
    "$MOCK_BIN_RESOLV/pidof" \
    "$MOCK_BIN_RESOLV/netstat" \
    "$MOCK_BIN_RESOLV/tailscale" \
    "$MOCK_BIN_RESOLV/logger" \
    "$MOCK_BIN_RESOLV/sleep" \
    "$TAILSCALED_INIT_RESOLV"

if EDGE_CONFIG_FILE="$CONFIG_RESOLV" \
   EDGE_RESOLV_CONF="$RESOLV_MISSING" \
   EDGE_TAILSCALED_INIT="$TAILSCALED_INIT_RESOLV" \
   EDGE_TEST_PATH_PREFIX="$MOCK_BIN_RESOLV" \
   "$HANDLER"
then
    echo "FAIL: handler succeeded although resolv.conf was missing"
    exit 1
fi

grep -q 'missing .*resolv.conf' "$LOGFILE_RESOLV"

if [ -s "$INIT_LOG_RESOLV" ]; then
    echo "FAIL: tailscaled restart was attempted"
    exit 1
fi

echo "PASS: missing resolv.conf is handled correctly"

echo "=== TEST: tailscaled restart fails ==="

TMPDIR_TSRESTART="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_TEST" "$TMPDIR_FAIL" "$TMPDIR_RESOLV" "$TMPDIR_TSRESTART"' EXIT HUP INT TERM

MOCK_BIN_TSRESTART="$TMPDIR_TSRESTART/bin"
mkdir -p "$MOCK_BIN_TSRESTART"

CONFIG_TSRESTART="$TMPDIR_TSRESTART/asus-edge.conf"
RESOLV_TSRESTART="$TMPDIR_TSRESTART/resolv.conf"
TAILSCALED_INIT_TSRESTART="$TMPDIR_TSRESTART/S06tailscaled"
LOGFILE_TSRESTART="$TMPDIR_TSRESTART/logger.log"

printf '%s\n' \
    'EDGE_UNBOUND_PORT=53535' \
    'EDGE_WAN_DNS_WAIT_SECONDS=1' \
    'EDGE_TAILSCALE_WAIT_SECONDS=1' \
    > "$CONFIG_TSRESTART"

printf '%s\n' 'nameserver 8.8.8.8' > "$RESOLV_TSRESTART"

printf '%s\n' \
    '#!/bin/sh' \
    'case "$1" in' \
    '  dnsmasq|unbound|tailscaled) echo 1234; exit 0 ;;' \
    'esac' \
    'exit 1' \
    > "$MOCK_BIN_TSRESTART/pidof"

printf '%s\n' \
    '#!/bin/sh' \
    'echo "tcp 0 0 127.0.0.1:53535 0.0.0.0:* LISTEN"' \
    > "$MOCK_BIN_TSRESTART/netstat"

printf '%s\n' \
    '#!/bin/sh' \
    'exit 0' \
    > "$MOCK_BIN_TSRESTART/tailscale"

printf '%s\n' \
    '#!/bin/sh' \
    "printf '%s\n' \"\$*\" >> \"$LOGFILE_TSRESTART\"" \
    > "$MOCK_BIN_TSRESTART/logger"

printf '%s\n' \
    '#!/bin/sh' \
    'exit 0' \
    > "$MOCK_BIN_TSRESTART/sleep"

printf '%s\n' \
    '#!/bin/sh' \
    'exit 1' \
    > "$TAILSCALED_INIT_TSRESTART"

chmod +x \
    "$MOCK_BIN_TSRESTART/pidof" \
    "$MOCK_BIN_TSRESTART/netstat" \
    "$MOCK_BIN_TSRESTART/tailscale" \
    "$MOCK_BIN_TSRESTART/logger" \
    "$MOCK_BIN_TSRESTART/sleep" \
    "$TAILSCALED_INIT_TSRESTART"

if EDGE_CONFIG_FILE="$CONFIG_TSRESTART" \
   EDGE_RESOLV_CONF="$RESOLV_TSRESTART" \
   EDGE_TAILSCALED_INIT="$TAILSCALED_INIT_TSRESTART" \
   EDGE_TEST_PATH_PREFIX="$MOCK_BIN_TSRESTART" \
   "$HANDLER"
then
    echo "FAIL: handler succeeded although tailscaled restart failed"
    exit 1
fi

grep -q 'failed to restart tailscaled after WAN DNS update' "$LOGFILE_TSRESTART"

echo "PASS: tailscaled restart failure is handled correctly"
