#!/usr/bin/bash
set -u
umask 077

ROUTERCLOUD_HOST="${ROUTERCLOUD_BACKUP_HOST:-192.168.50.1}"
ROUTERCLOUD_USER="${ROUTERCLOUD_BACKUP_USER:-admin1}"
ROUTERCLOUD_SSH_PORT="${ROUTERCLOUD_BACKUP_SSH_PORT:-1122}"
ROUTERCLOUD_REMOTE="${ROUTERCLOUD_BACKUP_REMOTE:-/tmp/mnt/ROUTER_DATA/RouterCloud/}"
KEY="${ROUTERCLOUD_BACKUP_KEY:-$HOME/.ssh/id_ed25519_routercloud_backup}"

STATE_DIR="${ROUTERCLOUD_BACKUP_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/routercloud-backup}"
STAGING="${ROUTERCLOUD_BACKUP_STAGING:-$STATE_DIR/staging}"
STATUS_FILE="$STATE_DIR/status.env"
RSYNC_LOG="$STATE_DIR/last-rsync.log"
RESTIC_LOG="$STATE_DIR/last-restic.log"
LOCK_FILE="${XDG_RUNTIME_DIR:-/tmp}/routercloud-backup-${UID}.lock"

BACKUP_MOUNT="${ROUTERCLOUD_BACKUP_MOUNT:-/mnt/dysk-lokalny}"
REPO="${ROUTERCLOUD_RESTIC_REPO:-$BACKUP_MOUNT/backups/routercloud-restic}"
PASSFILE="${ROUTERCLOUD_RESTIC_PASSWORD_FILE:-$HOME/.config/routercloud-backup/restic-password}"

REMOTE_SOURCE="${ROUTERCLOUD_USER}@${ROUTERCLOUD_HOST}:${ROUTERCLOUD_REMOTE}"

SSH_CMD="/usr/bin/ssh -F /dev/null -o IdentityFile=none -i $KEY -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no -o PreferredAuthentications=publickey -o StrictHostKeyChecking=yes -o ConnectTimeout=10 -p $ROUTERCLOUD_SSH_PORT"

mkdir -p "$STATE_DIR" "$STAGING"

exec 9>"$LOCK_FILE"

if ! /usr/bin/flock -n 9; then
    echo "RouterCloud backup: another run is already active"
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

    "$HOME/.local/bin/routercloud-backup-metrics" backup >/dev/null 2>&1 || true
}

fail_run() {
    RC="$1"
    STAGE="$2"
    echo "RouterCloud backup: failed at stage=$STAGE rc=$RC" >&2
    write_status "failure" "$RC" "$STAGE"
    exit "$RC"
}

echo "RouterCloud backup: started at $START_TIME"

if ! mountpoint -q "$BACKUP_MOUNT"; then
    fail_run 70 "backup-disk-not-mounted"
fi

if [ ! -r "$PASSFILE" ]; then
    fail_run 71 "password-file"
fi

if [ ! -f "$REPO/config" ]; then
    fail_run 72 "restic-repository"
fi

if /usr/bin/rsync -rtv --delete \
    --rsync-path=/opt/bin/rsync \
    -e "$SSH_CMD" \
    "$REMOTE_SOURCE" \
    "$STAGING/" \
    > "$RSYNC_LOG" 2>&1
then
    :
else
    RC=$?
    fail_run "$RC" "rsync-pull"
fi

chmod 0600 "$RSYNC_LOG"

if /usr/bin/restic \
    --repo "$REPO" \
    --password-file "$PASSFILE" \
    backup "$STAGING" \
    --tag routercloud \
    --tag scheduled \
    > "$RESTIC_LOG" 2>&1
then
    :
else
    RC=$?
    fail_run "$RC" "restic-backup"
fi

chmod 0600 "$RESTIC_LOG"

write_status "success" 0 "complete"

echo "RouterCloud backup: completed successfully"
exit 0
