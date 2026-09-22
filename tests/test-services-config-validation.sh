#!/bin/sh

set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

BASE_CONFIG="$TMP_DIR/base.conf"
cat >"$BASE_CONFIG" <<'EOF'
EDGE_OPT_WAIT_SECONDS="90"
EDGE_RUN_RC_UNSLUNG="0"
EDGE_ENTWARE_START_WAIT_SECONDS="330"
EDGE_ENTWARE_QUIET_SECONDS="20"
EDGE_SERVICE_STABILITY_SECONDS="5"
EDGE_SERVICE_START_ATTEMPTS="6"
EDGE_SERVICE_RETRY_SECONDS="5"
EDGE_ENABLE_EXIT_NODE="0"
EDGE_ACCEPT_DNS="false"
EDGE_REQUIRE_SWAP="0"
EDGE_SWAP_WAIT_SECONDS="60"
EDGE_TS_READY_WAIT_SECONDS="20"
EDGE_TS_NETFILTER_MODE="off"
EOF

expect_rejected() {
    variable_name="$1"
    invalid_value="$2"
    config_file="$TMP_DIR/$variable_name.conf"

    cp "$BASE_CONFIG" "$config_file"
    printf '%s="%s"\n' "$variable_name" "$invalid_value" >>"$config_file"

    if EDGE_CONFIG_FILE="$config_file" sh "$REPO_DIR/router/scripts/services-start" >/dev/null 2>&1; then
        echo "FAIL: invalid $variable_name=$invalid_value was accepted" >&2
        exit 1
    fi
}

for timing_name in \
    EDGE_OPT_WAIT_SECONDS \
    EDGE_ENTWARE_START_WAIT_SECONDS \
    EDGE_ENTWARE_QUIET_SECONDS \
    EDGE_SERVICE_STABILITY_SECONDS \
    EDGE_SERVICE_START_ATTEMPTS \
    EDGE_SERVICE_RETRY_SECONDS \
    EDGE_SWAP_WAIT_SECONDS \
    EDGE_TS_READY_WAIT_SECONDS
do
    expect_rejected "$timing_name" 0
    expect_rejected "$timing_name" abc
done

expect_rejected EDGE_RUN_RC_UNSLUNG 2
expect_rejected EDGE_ENABLE_EXIT_NODE 2
expect_rejected EDGE_ACCEPT_DNS yes
expect_rejected EDGE_REQUIRE_SWAP maybe
expect_rejected EDGE_TS_NETFILTER_MODE on

for bad_path in "" "/" "/opt" "/tmp/edge.sock" "/jffs/configs/asus-edge.conf" "../edge.sock" "/var/run/tailscale/../edge.sock"; do
    expect_rejected EDGE_TS_SOCKET "$bad_path"
done
for bad_path in "" "/" "/opt" "/tmp/tailscaled.state" "/jffs/configs/asus-edge.conf" "../tailscaled.state"; do
    expect_rejected EDGE_TS_STATE "$bad_path"
done
for bad_path in "" "/" "/opt" "/tmp/tailscaled.log" "/jffs/configs/asus-edge.conf" "../tailscaled.log"; do
    expect_rejected EDGE_TAILSCALED_LOG "$bad_path"
done
for bad_path in "" "/" "/opt" "/tmp/unbound.pid" "/jffs/configs/asus-edge.conf" "../unbound.pid"; do
    expect_rejected EDGE_UNBOUND_PIDFILE "$bad_path"
done

echo "PASS: invalid services-start configuration rejected"
