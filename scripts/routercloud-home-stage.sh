#!/usr/bin/env bash
# Stage a reconciled RouterCloud Home AJAX JS on ASUS without activating it.
# Fedora usage: bash scripts/routercloud-home-stage.sh admin1@ROUTER_HOST [SSH_PORT]
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
    echo "USAGE: $0 admin1@ROUTER_HOST [SSH_PORT]" >&2
    exit 2
fi

TARGET="$1"
PORT=1122
if [[ $# -eq 2 ]]; then PORT="$2"; fi

case "$TARGET" in
    admin1@?*) ;;
    *) echo 'SSH_TARGET_INVALID=STOP' >&2; exit 2 ;;
esac

case "$PORT" in
    ''|*[!0-9]*) echo 'SSH_PORT_INVALID=STOP' >&2; exit 2 ;;
esac

SOURCE="$HOME/Archiwa/RouterCloud-Home-AJAX-20261012/index.candidate.js"
EXPECTED_CANDIDATE='90171cdb676cb39de41a8e74384ac509294c617ae31a0b06735f5f7f527bcb0c'

if [[ ! -f "$SOURCE" || -L "$SOURCE" ]]; then
    echo 'LOCAL_CANDIDATE_INVALID=STOP' >&2
    exit 3
fi

SHA="$(sha256sum "$SOURCE" | cut -d ' ' -f 1)"
BYTES="$(wc -c < "$SOURCE" | tr -d '[:space:]')"

if [[ "$SHA" != "$EXPECTED_CANDIDATE" || "$BYTES" != 92809 ]]; then
    echo 'LOCAL_CANDIDATE_INTEGRITY=STOP' >&2
    exit 3
fi

echo 'LOCAL_CANDIDATE=PASS'
echo '=== ROUTERCLOUD CANDIDATE STAGING ==='

# SSH runs a fixed, self-contained POSIX command. stdin is the candidate
# file itself, not a shell script. Only a new private staged file is written.
ssh -T -p "$PORT" "$TARGET" '
    set -eu

    BACKUP_DIR=/opt/var/backups/routercloud-home-ajax-20261012
    ACTIVE=/opt/share/routercloud-password-recovery-20261003-163712/index.js
    ROLLBACK="$BACKUP_DIR/index.js"
    STAGE="$BACKUP_DIR/index.candidate.js"
    OLD_SHA=d5052ea33917bad9314a49792bc555dd2e7ce2a3f2532aaff3b83c23e4c593b4
    NEW_SHA=90171cdb676cb39de41a8e74384ac509294c617ae31a0b06735f5f7f527bcb0c

    if [ ! -d "$BACKUP_DIR" ] || [ -L "$BACKUP_DIR" ] ||
       [ ! -r "$ROLLBACK" ] || [ -L "$ROLLBACK" ] ||
       [ ! -r "$ACTIVE" ] || [ -L "$ACTIVE" ]; then
        echo "ROUTER_BASELINE_INVALID=STOP" >&2
        exit 4
    fi

    if [ -e "$STAGE" ] || [ -L "$STAGE" ]; then
        echo "STAGED_FILE_ALREADY_EXISTS=STOP" >&2
        exit 4
    fi

    LIVE_NOW="$(sha256sum "$ACTIVE" | cut -d " " -f 1)"
    ROLLBACK_NOW="$(sha256sum "$ROLLBACK" | cut -d " " -f 1)"

    if [ "$LIVE_NOW" != "$OLD_SHA" ] ||
       [ "$ROLLBACK_NOW" != "$OLD_SHA" ]; then
        echo "LIVE_OR_ROLLBACK_HASH_CHANGED=STOP" >&2
        exit 4
    fi

    echo "LIVE_AND_ROLLBACK_INTEGRITY=PASS"

    umask 077
    TEMP="$BACKUP_DIR/.index.candidate.part.$$"
    if [ -e "$TEMP" ] || [ -L "$TEMP" ]; then
        echo "TEMP_FILE_COLLISION=STOP" >&2
        exit 4
    fi
    trap "rm -f \"$TEMP\"" 0 1 2 15

    cat > "$TEMP"

    NEW_NOW="$(sha256sum "$TEMP" | cut -d " " -f 1)"
    STAGED_BYTES="$(wc -c < "$TEMP" | tr -d "[:space:]")"

    if [ "$NEW_NOW" != "$NEW_SHA" ] || [ "$STAGED_BYTES" != 92809 ]; then
        echo "TRANSFER_INTEGRITY=FAIL" >&2
        exit 5
    fi

    chmod 600 "$TEMP"
    mv "$TEMP" "$STAGE"

    if [ "$(sha256sum "$STAGE" | cut -d " " -f 1)" != "$NEW_SHA" ]; then
        echo "STAGING_VERIFICATION=FAIL" >&2
        exit 5
    fi

    if [ "$(sha256sum "$ACTIVE" | cut -d " " -f 1)" != "$OLD_SHA" ]; then
        echo "LIVE_CHANGED_UNEXPECTEDLY=STOP" >&2
        exit 5
    fi

    echo "STAGING_VERIFICATION=PASS"
    echo "STAGED_BYTES=$STAGED_BYTES"
    echo "LIVE_INDEX_UNCHANGED=YES"
    echo "ROUTERCLOUD_RESTARTED=NO"
    echo "STAGED_PATH=$STAGE"
    echo "=== STAGING COMPLETE ==="
' < "$SOURCE"
