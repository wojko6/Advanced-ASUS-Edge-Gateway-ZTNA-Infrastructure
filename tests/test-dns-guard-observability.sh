#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
GUARD="$ROOT_DIR/router/scripts/dns-guard"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

MOCK_BIN="$TMP_DIR/bin"
CONFIG="$TMP_DIR/asus-edge.conf"
RESOLV="$TMP_DIR/resolv.conf"
STATE_DIR="$TMP_DIR/state"
RUNTIME_STATE_DIR="$TMP_DIR/runtime"
FLAG="$STATE_DIR/dns-breakglass"

mkdir -p "$MOCK_BIN" "$STATE_DIR" "$RUNTIME_STATE_DIR"

cat >"$CONFIG" <<'EOF'
EDGE_UNBOUND_PORT=53535
EDGE_DNS_LOCAL_RESOLVER_IP=192.0.2.53
EDGE_DNS_FAILBACK_SUCCESS_THRESHOLD=3
EOF

cat >"$MOCK_BIN/nvram" <<'EOF'
#!/bin/sh
[ "$1" = "get" ] || exit 1
case "$2" in
    wan0_dns_r) echo "9.9.9.9 149.112.112.112" ;;
    wan0_dns|wan_dns_r|wan_dns) echo "" ;;
    ntp_ready) echo 1 ;;
    *) echo "" ;;
esac
EOF

cat >"$MOCK_BIN/logger" <<'EOF'
#!/bin/sh
exit 0
EOF
chmod +x "$MOCK_BIN/nvram" "$MOCK_BIN/logger"

run_metrics() {
    EDGE_CONFIG_FILE="$CONFIG" \
    EDGE_RESOLV_CONF="$RESOLV" \
    EDGE_DNS_STATE_DIR="$STATE_DIR" \
    EDGE_DNS_RUNTIME_STATE_DIR="$RUNTIME_STATE_DIR" \
    EDGE_DNS_BREAKGLASS_FLAG="$FLAG" \
    EDGE_TEST_PATH_PREFIX="$MOCK_BIN" \
        sh "$GUARD" metrics
}

printf '%s\n' '0' >"$RUNTIME_STATE_DIR/bootstrap-dns-healthy"
printf '%s\n' '1700000001' >"$RUNTIME_STATE_DIR/bootstrap-dns-last-check-epoch"
printf '%s\n' 'nameserver 9.9.9.9' 'nameserver 149.112.112.112' >"$RESOLV"
bootstrap_one="$(run_metrics)"
printf '%s\n' "$bootstrap_one" | grep -qx 'asus_edge_dns_guard_mode_bootstrap 1'
printf '%s\n' "$bootstrap_one" | grep -qx 'asus_edge_dns_guard_mode_local 0'
printf '%s\n' "$bootstrap_one" | grep -qx 'asus_edge_dns_guard_state_valid 1'
printf '%s\n' "$bootstrap_one" | grep -qx 'asus_edge_dns_guard_breakglass_active 0'
printf '%s\n' "$bootstrap_one" | grep -qx 'asus_edge_dns_guard_bootstrap_dns_healthy 0'
printf '%s\n' "$bootstrap_one" | grep -qx 'asus_edge_dns_guard_bootstrap_dns_last_check_timestamp_seconds 1700000001'
printf '%s\n' "$bootstrap_one" | grep -qx 'asus_edge_dns_guard_fallback_transitions_runtime_total 1'
fallback_since="$(printf '%s\n' "$bootstrap_one" | awk '$1=="asus_edge_dns_guard_fallback_since_timestamp_seconds"{print $2}')"
last_transition="$(printf '%s\n' "$bootstrap_one" | awk '$1=="asus_edge_dns_guard_last_transition_timestamp_seconds"{print $2}')"
[ "$fallback_since" -gt 0 ]
[ "$last_transition" -gt 0 ]

bootstrap_two="$(run_metrics)"
printf '%s\n' "$bootstrap_two" | grep -qx 'asus_edge_dns_guard_fallback_transitions_runtime_total 1'

printf '%s\n' 'nameserver 192.0.2.53' >"$RESOLV"
local_metrics="$(run_metrics)"
printf '%s\n' "$local_metrics" | grep -qx 'asus_edge_dns_guard_mode_local 1'
printf '%s\n' "$local_metrics" | grep -qx 'asus_edge_dns_guard_mode_bootstrap 0'
printf '%s\n' "$local_metrics" | grep -qx 'asus_edge_dns_guard_fallback_since_timestamp_seconds 0'
printf '%s\n' "$local_metrics" | grep -qx 'asus_edge_dns_guard_fallback_transitions_runtime_total 1'

: >"$FLAG"
breakglass_metrics="$(run_metrics)"
printf '%s\n' "$breakglass_metrics" | grep -qx 'asus_edge_dns_guard_breakglass_active 1'

printf '%s\n' 'nameserver 203.0.113.99' >"$RESOLV"
unknown_metrics="$(run_metrics)"
printf '%s\n' "$unknown_metrics" | grep -qx 'asus_edge_dns_guard_state_valid 0'
printf '%s\n' "$unknown_metrics" | grep -qx 'asus_edge_dns_guard_mode_local 0'
printf '%s\n' "$unknown_metrics" | grep -qx 'asus_edge_dns_guard_mode_bootstrap 0'

echo "PASS: DNS Guard coarse monitoring state contract"
