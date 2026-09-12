#!/bin/sh

set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
HANDLER="$REPO_DIR/router/scripts/wan-event-handler"
TMP_DIR="$(mktemp -d)"
MOCK_BIN="$TMP_DIR/bin"
CONFIG="$TMP_DIR/edge.conf"
LOGFILE="$TMP_DIR/logger.log"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$MOCK_BIN"

cat >"$MOCK_BIN/logger" <<EOF
#!/bin/sh
printf '%s\n' "\$*" >>"$LOGFILE"
EOF
chmod +x "$MOCK_BIN/logger"

expect_invalid() {
    expected="$1"
    shift
    : >"$LOGFILE"
    printf '%s\n' "$@" >"$CONFIG"

    if EDGE_CONFIG_FILE="$CONFIG" \
        EDGE_TEST_PATH_PREFIX="$MOCK_BIN" \
        "$HANDLER" >/dev/null 2>&1; then
        echo "FAIL: invalid WAN recovery configuration was accepted" >&2
        exit 1
    fi

    grep -F "$expected" "$LOGFILE" >/dev/null || {
        echo "FAIL: expected validation error not logged: $expected" >&2
        exit 1
    }
}

expect_invalid 'EDGE_WAN_DNS_WAIT_SECONDS must be a positive integer' \
    'EDGE_WAN_DNS_WAIT_SECONDS=abc' \
    'EDGE_TAILSCALE_WAIT_SECONDS=20' \
    'EDGE_UNBOUND_PORT=53535'

expect_invalid 'EDGE_WAN_DNS_WAIT_SECONDS must be greater than zero' \
    'EDGE_WAN_DNS_WAIT_SECONDS=0' \
    'EDGE_TAILSCALE_WAIT_SECONDS=20' \
    'EDGE_UNBOUND_PORT=53535'

expect_invalid 'EDGE_TAILSCALE_WAIT_SECONDS must be a positive integer' \
    'EDGE_WAN_DNS_WAIT_SECONDS=30' \
    'EDGE_TAILSCALE_WAIT_SECONDS=-1' \
    'EDGE_UNBOUND_PORT=53535'

expect_invalid 'EDGE_UNBOUND_PORT must be an integer between 1 and 65535' \
    'EDGE_WAN_DNS_WAIT_SECONDS=30' \
    'EDGE_TAILSCALE_WAIT_SECONDS=20' \
    'EDGE_UNBOUND_PORT=not-a-port'

expect_invalid 'EDGE_UNBOUND_PORT must be between 1 and 65535' \
    'EDGE_WAN_DNS_WAIT_SECONDS=30' \
    'EDGE_TAILSCALE_WAIT_SECONDS=20' \
    'EDGE_UNBOUND_PORT=65536'

echo 'PASS: invalid WAN recovery configuration rejected'
