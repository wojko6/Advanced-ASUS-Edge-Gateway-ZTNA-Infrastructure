#!/usr/bin/bash
set -u
umask 077

KIND="${1:-}"
STATE_DIR="${ROUTERCLOUD_BACKUP_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/routercloud-backup}"
VM_URL="${ROUTERCLOUD_VM_IMPORT_URL:-http://127.0.0.1:8428/api/v1/import/prometheus}"

case "$KIND" in
    backup)
        STATUS_FILE="$STATE_DIR/status.env"
        PREFIX="routercloud_backup"
        ;;
    maintenance)
        STATUS_FILE="$STATE_DIR/maintenance-status.env"
        PREFIX="routercloud_maintenance"
        ;;
    *)
        exit 64
        ;;
esac

[ -r "$STATUS_FILE" ] || exit 66

RESULT="$(awk -F= '$1=="LAST_RESULT"{print $2}' "$STATUS_FILE")"
RC="$(awk -F= '$1=="LAST_RC"{print $2}' "$STATUS_FILE")"
END="$(awk '$0 ~ /^LAST_END=/{sub(/^LAST_END=/,""); print}' "$STATUS_FILE")"
DURATION="$(awk -F= '$1=="LAST_DURATION_SECONDS"{print $2}' "$STATUS_FILE")"

case "$RESULT" in
    success) SUCCESS=1 ;;
    *)       SUCCESS=0 ;;
esac

case "$RC" in
    ''|*[!0-9-]*) exit 65 ;;
esac

case "$DURATION" in
    ''|*[!0-9]*) exit 65 ;;
esac

END_EPOCH="$(date -d "$END" +%s)" || exit 65

printf '%s\n' \
    "${PREFIX}_last_run_success $SUCCESS" \
    "${PREFIX}_last_run_timestamp_seconds $END_EPOCH" \
    "${PREFIX}_last_duration_seconds $DURATION" \
    "${PREFIX}_last_rc $RC" \
| curl -fsS \
    --connect-timeout 2 \
    --max-time 5 \
    --data-binary @- \
    "$VM_URL" \
    >/dev/null

exit $?
