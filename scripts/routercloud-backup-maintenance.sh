#!/usr/bin/bash
set -u
umask 077

STATE_DIR="${ROUTERCLOUD_BACKUP_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/routercloud-backup}"
STATUS_FILE="$STATE_DIR/maintenance-status.env"
RETENTION_LOG="$STATE_DIR/last-retention.log"
CHECK_LOG="$STATE_DIR/last-check.log"

BACKUP_MOUNT="${ROUTERCLOUD_BACKUP_MOUNT:-/mnt/dysk-lokalny}"
REPO="${ROUTERCLOUD_RESTIC_REPO:-$BACKUP_MOUNT/backups/routercloud-restic}"
PASSFILE="${ROUTERCLOUD_RESTIC_PASSWORD_FILE:-$HOME/.config/routercloud-backup/restic-password}"

LOCK_FILE="${XDG_RUNTIME_DIR:-/tmp}/routercloud-backup-${UID}.lock"

mkdir -p "$STATE_DIR"

exec 9>"$LOCK_FILE"

if ! /usr/bin/flock -n 9; then
    echo "RouterCloud maintenance: backup/maintenance already active"
    exit 0
fi

START_EPOCH="$(date +%s)"
START_TIME="$(date -Is)"

write_status() {
    RESULT="$1"
    RC="$2"
    STAGE="$3"

    END_EPOCH="$(date +%s)"
    END_TIME="$(date -Is)"
    DURATION="$((END_EPOCH - START_EPOCH))"
    TMP_STATUS="$STATUS_FILE.tmp"

    {
        echo "LAST_RESULT=$RESULT"
        echo "LAST_RC=$RC"
        echo "LAST_STAGE=$STAGE"
        echo "LAST_START=$START_TIME"
        echo "LAST_END=$END_TIME"
        echo "LAST_DURATION_SECONDS=$DURATION"
    } > "$TMP_STATUS"

    mv "$TMP_STATUS" "$STATUS_FILE"
    chmod 0600 "$STATUS_FILE"

    "$HOME/.local/bin/routercloud-backup-metrics" maintenance >/dev/null 2>&1 || true
}

fail_run() {
    RC="$1"
    STAGE="$2"
    echo "RouterCloud maintenance: failed at stage=$STAGE rc=$RC" >&2
    write_status "failure" "$RC" "$STAGE"
    exit "$RC"
}

echo "RouterCloud maintenance: started at $START_TIME"

if ! mountpoint -q "$BACKUP_MOUNT"; then
    fail_run 70 "backup-disk-not-mounted"
fi

if [ ! -r "$PASSFILE" ]; then
    fail_run 71 "password-file"
fi

if [ ! -f "$REPO/config" ]; then
    fail_run 72 "restic-repository"
fi

echo "RouterCloud maintenance: retention/prune"

if /usr/bin/restic \
    --repo "$REPO" \
    --password-file "$PASSFILE" \
    forget \
    --tag scheduled \
    --keep-within 48h \
    --keep-daily 14 \
    --keep-weekly 8 \
    --keep-monthly 12 \
    --keep-yearly 3 \
    --prune \
    > "$RETENTION_LOG" 2>&1
then
    :
else
    RC=$?
    fail_run "$RC" "retention-prune"
fi

chmod 0600 "$RETENTION_LOG"

echo "RouterCloud maintenance: integrity check"

if /usr/bin/restic \
    --repo "$REPO" \
    --password-file "$PASSFILE" \
    check \
    --read-data \
    > "$CHECK_LOG" 2>&1
then
    :
else
    RC=$?
    fail_run "$RC" "restic-check"
fi

chmod 0600 "$CHECK_LOG"

write_status "success" 0 "complete"

echo "RouterCloud maintenance: completed successfully"
exit 0
