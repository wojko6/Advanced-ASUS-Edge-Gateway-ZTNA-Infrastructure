#!/usr/bin/bash
set -euo pipefail

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
EXPORTER="$ROOT_DIR/scripts/dns-guard-metrics.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM
PAYLOAD="$TMP_DIR/payload"

cat >"$TMP_DIR/ssh" <<'EOF'
#!/usr/bin/bash
cat <<'METRICS'
asus_edge_dns_guard_mode_local 0
asus_edge_dns_guard_mode_bootstrap 1
asus_edge_dns_guard_state_valid 1
asus_edge_dns_guard_breakglass_active 0
asus_edge_dns_guard_last_transition_timestamp_seconds 1700000000
asus_edge_dns_guard_fallback_transitions_runtime_total 4
asus_edge_dns_guard_fallback_since_timestamp_seconds 1700000000
METRICS
EOF

cat >"$TMP_DIR/curl" <<EOF
#!/usr/bin/bash
cat >"$PAYLOAD"
EOF

chmod +x "$TMP_DIR/ssh" "$TMP_DIR/curl"

ROUTER_HOST=router.example \
ROUTER_USER=operator \
ROUTER_PORT=1122 \
SSH_TIMEOUT=5 \
DNS_GUARD_SSH_BIN="$TMP_DIR/ssh" \
DNS_GUARD_CURL_BIN="$TMP_DIR/curl" \
DNS_GUARD_VM_IMPORT_URL=http://127.0.0.1:8428/api/v1/import/prometheus \
    "$EXPORTER"

grep -qx 'asus_edge_dns_guard_mode_bootstrap 1' "$PAYLOAD"
grep -qx 'asus_edge_dns_guard_breakglass_active 0' "$PAYLOAD"
grep -qx 'asus_edge_dns_guard_fallback_transitions_runtime_total 4' "$PAYLOAD"
grep -E '^asus_edge_dns_guard_collection_timestamp_seconds [0-9]+$' "$PAYLOAD" >/dev/null

echo "PASS: DNS Guard Fedora metrics exporter validates and forwards coarse state"
