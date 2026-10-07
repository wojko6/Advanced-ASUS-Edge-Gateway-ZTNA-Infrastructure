#!/usr/bin/bash
set -euo pipefail

VM_URL="${VM_URL:-http://127.0.0.1:8428}"
VM_IMPORT_URL="${VM_IMPORT_URL:-$VM_URL/api/v1/import/prometheus}"
RULE_UID="routercloud_backup_bad"

cd "$(dirname "$0")/.."
REPO_DIR="$PWD"

echo '=== ROUTERCLOUD ALERT LIVE E2E ==='

sudo -v

query_value() {
    local query="$1"

    curl -fsSG "$VM_URL/api/v1/query" \
        --data-urlencode "query=$query" |
    jq -r '
        if .status != "success" then
            "QUERY_ERROR"
        elif (.data.result | length) != 1 then
            "RESULT_COUNT_" + ((.data.result | length) | tostring)
        else
            .data.result[0].value[1]
        end
    '
}

grafana_state() {
    sudo python3 - <<'PY'
import sqlite3

db = "/var/lib/grafana/grafana.db"

con = sqlite3.connect(
    f"file:{db}?mode=ro",
    uri=True,
)

row = con.execute(
    """
    SELECT
        current_state,
        current_state_since,
        last_eval_time,
        last_error
    FROM alert_instance
    WHERE rule_uid = ?
    ORDER BY last_eval_time DESC
    LIMIT 1
    """,
    ("routercloud_backup_bad",),
).fetchone()

if row is None:
    print("NONE")
else:
    state, since, last_eval, last_error = row
    print(state or "UNKNOWN")
PY
}

restore_health() {
    echo '--- restoring real backup metrics ---'

    if "$REPO_DIR/scripts/routercloud-backup-metrics.sh" backup
    then
        echo "RESTORE_SOURCE=status.env"
    else
        echo "WARN: status.env restore failed; restoring verified healthy value directly" >&2

        printf '%s\n' \
            'routercloud_backup_last_run_success 1' \
        | curl -fsS \
            --data-binary @- \
            "$VM_IMPORT_URL" \
            >/dev/null
    fi
}

wait_for_firing() {
    local deadline=$((SECONDS + 190))
    local state=""

    while (( SECONDS < deadline )); do
        state="$(grafana_state)"
        printf 'STATE=%s\n' "$state"

        case "$state" in
            Alerting|Firing)
                return 0
                ;;
        esac

        sleep 10
    done

    return 1
}

wait_for_recovery() {
    local deadline=$((SECONDS + 190))
    local state=""

    while (( SECONDS < deadline )); do
        state="$(grafana_state)"
        printf 'STATE=%s\n' "$state"

        case "$state" in
            NONE|Normal)
                return 0
                ;;
        esac

        sleep 10
    done

    return 1
}

trap restore_health EXIT HUP INT TERM

echo
echo '=== 1. PREFLIGHT HEALTH ==='

BEFORE="$(
    query_value \
    'last_over_time(routercloud_backup_last_run_success[24h])'
)"

echo "METRIC_BEFORE=$BEFORE"

test "$BEFORE" = "1" || {
    echo "FAIL: backup metric is not healthy before test"
    exit 1
}

echo
echo '=== 2. INJECT SYNTHETIC FAILURE ==='

printf '%s\n' \
    'routercloud_backup_last_run_success 0' \
| curl -fsS \
    --data-binary @- \
    "$VM_IMPORT_URL" \
    >/dev/null

sleep 2

AFTER_INJECTION="$(
    query_value \
    'last_over_time(routercloud_backup_last_run_success[24h])'
)"

echo "METRIC_AFTER_INJECTION=$AFTER_INJECTION"

test "$AFTER_INJECTION" = "0" || {
    echo "FAIL: synthetic failure was not visible in VictoriaMetrics"
    exit 1
}

echo
echo '=== 3. WAIT FOR FIRING ==='

if ! wait_for_firing
then
    echo "FAIL: $RULE_UID did not reach Alerting/Firing"
    exit 1
fi

echo "FIRING_DETECTED=PASS"

echo
echo '=== 4. RESTORE HEALTHY METRIC ==='

restore_health

sleep 2

AFTER_RESTORE="$(
    query_value \
    'last_over_time(routercloud_backup_last_run_success[24h])'
)"

echo "METRIC_AFTER_RESTORE=$AFTER_RESTORE"

test "$AFTER_RESTORE" = "1" || {
    echo "FAIL: metric did not return to healthy value"
    exit 1
}

echo
echo '=== 5. WAIT FOR RECOVERY ==='

if ! wait_for_recovery
then
    echo "FAIL: $RULE_UID did not recover to Normal/NONE"
    exit 1
fi

echo "RECOVERY_DETECTED=PASS"

echo
echo '=== 6. FINAL METRIC ==='

FINAL="$(
    query_value \
    'last_over_time(routercloud_backup_last_run_success[24h])'
)"

echo "FINAL_METRIC=$FINAL"

test "$FINAL" = "1" || {
    echo "FAIL: final metric is not healthy"
    exit 1
}

trap - EXIT HUP INT TERM

echo
echo 'ROUTERCLOUD_ALERT_LIVE_E2E=PASS'
