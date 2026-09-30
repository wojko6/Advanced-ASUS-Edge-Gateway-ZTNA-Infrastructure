#!/usr/bin/bash
set -u
umask 077

SOURCE="${ROUTERCLOUD_SOURCE:-$HOME/RouterCloud/}"
ROUTERCLOUD_HOST="${ROUTERCLOUD_HOST:-192.168.50.1}"
ROUTERCLOUD_USER="${ROUTERCLOUD_USER:-admin1}"
ROUTERCLOUD_SSH_PORT="${ROUTERCLOUD_SSH_PORT:-1122}"
DEST="${ROUTERCLOUD_USER}@${ROUTERCLOUD_HOST}:/tmp/mnt/ROUTER_DATA/RouterCloud/"
KEY="${ROUTERCLOUD_KEY:-$HOME/.ssh/id_ed25519_routercloud}"

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/routercloud-sync"
LOCK_FILE="${XDG_RUNTIME_DIR:-/tmp}/routercloud-sync-${UID}.lock"
STATUS_FILE="$STATE_DIR/status.env"

mkdir -p "$STATE_DIR"

exec 9>"$LOCK_FILE"
if ! /usr/bin/flock -n 9; then
    echo "RouterCloud: another sync is already running"
    exit 0
fi

START_EPOCH="$(date +%s)"
START_TIME="$(date -Is)"

echo "RouterCloud: sync started at $START_TIME"

if /usr/bin/rsync -rtv \
    --rsync-path=/opt/bin/rsync \
    -e "/usr/bin/ssh -i $KEY -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 -p $ROUTERCLOUD_SSH_PORT" \
    "$SOURCE" \
    "$DEST"
then
    RC=0
    RESULT="success"
else
    RC=$?
    RESULT="failure"
fi

END_EPOCH="$(date +%s)"
END_TIME="$(date -Is)"
DURATION="$((END_EPOCH - START_EPOCH))"
TMP_STATUS="$STATUS_FILE.tmp"

{
    echo "LAST_RESULT=$RESULT"
    echo "LAST_RC=$RC"
    echo "LAST_START=$START_TIME"
    echo "LAST_END=$END_TIME"
    echo "LAST_DURATION_SECONDS=$DURATION"
} > "$TMP_STATUS"

mv "$TMP_STATUS" "$STATUS_FILE"
chmod 0600 "$STATUS_FILE"

if [ "$RC" -eq 0 ]; then
    echo "RouterCloud: sync completed successfully in ${DURATION}s"
else
    echo "RouterCloud: sync failed with rc=$RC" >&2
fi

exit "$RC"
