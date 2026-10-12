#!/bin/sh
# RouterCloud Home AJAX: bounded UI-only activation on ASUS.
# From Fedora, after explicit authorization:
#   ssh -T -p 1122 admin1@192.168.50.1 'sh -s' < scripts/routercloud-home-activate.sh
# Only the active external JS is replaced; RouterCloud service is restarted.
set -eu

echo '=== ROUTERCLOUD HOME AJAX PRODUCTION ACTIVATION ==='

CONF=/opt/etc/dufs-personal-cloud.yaml
INIT=/opt/etc/init.d/S67routercloud
ASSET_DIR=/opt/share/routercloud-password-recovery-20261003-163712
LIVE="$ASSET_DIR/index.js"
BACKUP_DIR=/opt/var/backups/routercloud-home-ajax-20261012
BACKUP="$BACKUP_DIR/index.js"
STAGED="$BACKUP_DIR/index.candidate.js"
OLD_SHA=d5052ea33917bad9314a49792bc555dd2e7ce2a3f2532aaff3b83c23e4c593b4
NEW_SHA=90171cdb676cb39de41a8e74384ac509294c617ae31a0b06735f5f7f527bcb0c
OLD_REV=503161dd5bee21ac
NEW_REV=a6b8ba062e194c1e

fail() {
    echo "ACTIVATION=STOP reason=$1" >&2
    exit 1
}

getsha() { sha256sum "$1" | awk '{print $1}'; }

revision() {
    (
        cd "$ASSET_DIR" || exit 1
        for name in index.html index.css index.js favicon.ico; do
            printf '%s' "$name"
            cat "$name"
        done
    ) | sha256sum | awk '{print substr($1,1,16)}'
}

[ "$(id -u)" = 0 ] || fail NOT_ROOT
[ -r "$CONF" ] || fail YAML_UNREADABLE
[ -x "$INIT" ] || fail ROUTERCLOUD_INIT_NOT_EXECUTABLE
[ -d "$ASSET_DIR" ] && [ ! -L "$ASSET_DIR" ] ||
    fail ASSET_DIR_CHANGED
[ -d "$BACKUP_DIR" ] && [ ! -L "$BACKUP_DIR" ] ||
    fail BACKUP_DIR_CHANGED

CONFIGURED="$(awk '
    /^[[:space:]]*assets:[[:space:]]*/ {
        sub(/^[[:space:]]*assets:[[:space:]]*/, "")
        gsub(/"/, "")
        sub(/[[:space:]]*$/, "")
        print
        exit
    }' "$CONF")"
[ "$CONFIGURED" = "$ASSET_DIR" ] || fail YAML_ASSET_PATH_CHANGED

for file in "$LIVE" "$BACKUP" "$STAGED" \
    "$ASSET_DIR/index.html" "$ASSET_DIR/index.css" \
    "$ASSET_DIR/favicon.ico"; do
    [ -f "$file" ] && [ -r "$file" ] && [ ! -L "$file" ] ||
        fail MISSING_FILE_OR_SYMLINK
done

[ "$(getsha "$LIVE")" = "$OLD_SHA" ] || fail LIVE_SHA_CHANGED
[ "$(getsha "$BACKUP")" = "$OLD_SHA" ] || fail BACKUP_SHA_CHANGED
[ "$(getsha "$STAGED")" = "$NEW_SHA" ] || fail STAGED_SHA_CHANGED
[ "$(wc -c < "$STAGED" | tr -d '[:space:]')" = 92809 ] ||
    fail STAGED_SIZE_CHANGED
[ "$(revision)" = "$OLD_REV" ] || fail LIVE_REVISION_CHANGED

# Confirm what the new version would be without changing a file yet.
PREDICTED="$(
    (
        cd "$ASSET_DIR" || exit 1
        for name in index.html index.css index.js favicon.ico; do
            printf '%s' "$name"
            if [ "$name" = index.js ]; then
                cat "$STAGED"
            else
                cat "$name"
            fi
        done
    ) | sha256sum | awk '{print substr($1,1,16)}'
)"
[ "$PREDICTED" = "$NEW_REV" ] || fail PREDICTED_REVISION_CHANGED

echo 'RECHECK_LIVE_AND_ROLLBACK=PASS'
echo 'RECHECK_STAGED_CANDIDATE=PASS'
echo "EXPECTED_NEW_ASSETS_REV=$NEW_REV"

TEMP=''
SWAPPED=NO
SUCCESS=NO

on_exit() {
    RC=$?
    trap - 0
    if [ -n "$TEMP" ] && [ -e "$TEMP" ]; then
        rm -f "$TEMP"
    fi
    if [ "$SWAPPED" = YES ] && [ "$SUCCESS" != YES ]; then
        echo 'AUTO_ROLLBACK=START'
        RESTORE_TEMP="$ASSET_DIR/.index.js.routercloud-restore.$$"
        if [ ! -e "$RESTORE_TEMP" ] &&
           cp "$BACKUP" "$RESTORE_TEMP" &&
           chown 0:0 "$RESTORE_TEMP" &&
           chmod 0644 "$RESTORE_TEMP" &&
           mv -f "$RESTORE_TEMP" "$LIVE"; then
            echo 'AUTO_ROLLBACK_FILE=RESTORED'
            if "$INIT" restart; then
                echo 'AUTO_ROLLBACK_RESTART_COMMAND=PASS'
            else
                echo 'AUTO_ROLLBACK_RESTART_COMMAND=FAIL' >&2
            fi
            if [ "$(getsha "$LIVE")" = "$OLD_SHA" ]; then
                echo 'AUTO_ROLLBACK_HASH=PASS'
            else
                echo 'AUTO_ROLLBACK_HASH=FAIL' >&2
            fi
        else
            echo 'AUTO_ROLLBACK_FILE=FAIL' >&2
        fi
    fi
    exit "$RC"
}
trap 'on_exit' 0

umask 077
TEMP="$(mktemp "$ASSET_DIR/.index.js.routercloud-home-XXXXXX")"
cp "$STAGED" "$TEMP"
[ "$(getsha "$TEMP")" = "$NEW_SHA" ] || fail TEMP_INTEGRITY
chown 0:0 "$TEMP"
chmod 0644 "$TEMP"
[ -f "$TEMP" ] && [ ! -L "$TEMP" ] || fail TEMP_FILE_INVALID

# The only production file mutation, on the same filesystem (atomic rename).
mv -f "$TEMP" "$LIVE"
TEMP=''
SWAPPED=YES
[ "$(getsha "$LIVE")" = "$NEW_SHA" ] || fail POST_SWAP_HASH

echo 'ACTIVE_INDEX_SWITCH=PASS'
echo 'RESTARTING_ROUTERCLOUD=YES'
if ! "$INIT" restart; then
    fail ROUTERCLOUD_RESTART_COMMAND_FAILED
fi

[ "$(getsha "$LIVE")" = "$NEW_SHA" ] || fail POST_RESTART_HASH
[ "$(revision)" = "$NEW_REV" ] || fail POST_RESTART_REVISION

SUCCESS=YES
echo 'ROUTERCLOUD_RESTART_COMMAND=PASS'
echo 'LIVE_INDEX_SHA256=90171cdb676cb39de41a8e74384ac509294c617ae31a0b06735f5f7f527bcb0c'
echo "LIVE_ASSETS_REV=$NEW_REV"
echo 'ACTIVATION=PASS'
echo 'FEDORA_HTTPS_BROWSER_ACCEPTANCE=PENDING'
echo '=== ACTIVATION COMPLETE ==='
