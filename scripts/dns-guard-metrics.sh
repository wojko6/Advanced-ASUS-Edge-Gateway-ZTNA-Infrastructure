#!/usr/bin/bash
set -euo pipefail
umask 077

PATH="/usr/local/bin:/usr/bin:/bin"

: "${ROUTER_HOST:?ROUTER_HOST is required}"
: "${ROUTER_USER:?ROUTER_USER is required}"
: "${ROUTER_PORT:=1122}"
: "${SSH_TIMEOUT:=10}"
: "${DNS_GUARD_VM_IMPORT_URL:=http://127.0.0.1:8428/api/v1/import/prometheus}"
: "${DNS_GUARD_SSH_BIN:=ssh}"
: "${DNS_GUARD_CURL_BIN:=curl}"

case "$ROUTER_PORT" in
    ''|*[!0-9]*) echo "ERROR: ROUTER_PORT must be numeric" >&2; exit 64 ;;
esac
case "$SSH_TIMEOUT" in
    ''|*[!0-9]*|0) echo "ERROR: SSH_TIMEOUT must be a positive integer" >&2; exit 64 ;;
esac

metrics="$(
    "$DNS_GUARD_SSH_BIN" \
        -p "$ROUTER_PORT" \
        -o BatchMode=yes \
        -o ConnectTimeout="$SSH_TIMEOUT" \
        "$ROUTER_USER@$ROUTER_HOST" \
        '/jffs/addons/asus-edge/bin/dns-guard metrics'
)"

required_metrics="
asus_edge_dns_guard_mode_local
asus_edge_dns_guard_mode_bootstrap
asus_edge_dns_guard_state_valid
asus_edge_dns_guard_breakglass_active
asus_edge_dns_guard_last_transition_timestamp_seconds
asus_edge_dns_guard_fallback_transitions_runtime_total
asus_edge_dns_guard_fallback_since_timestamp_seconds
"

for metric_name in $required_metrics; do
    metric_line="$(printf '%s\n' "$metrics" | awk -v name="$metric_name" '$1 == name {print; exit}')"
    [ -n "$metric_line" ] || {
        echo "ERROR: missing DNS Guard metric: $metric_name" >&2
        exit 65
    }

    metric_value="$(printf '%s\n' "$metric_line" | awk '{print $2}')"
    case "$metric_value" in
        ''|*[!0-9]*)
            echo "ERROR: invalid DNS Guard metric value for $metric_name" >&2
            exit 65
            ;;
    esac
done

collection_epoch="$(date +%s)"

{
    printf '%s\n' "$metrics"
    printf 'asus_edge_dns_guard_collection_timestamp_seconds %s\n' "$collection_epoch"
} |
    "$DNS_GUARD_CURL_BIN" -fsS \
        --connect-timeout 2 \
        --max-time 5 \
        --data-binary @- \
        "$DNS_GUARD_VM_IMPORT_URL" \
        >/dev/null
