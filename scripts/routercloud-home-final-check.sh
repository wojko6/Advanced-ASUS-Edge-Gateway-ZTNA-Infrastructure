#!/bin/sh
# RouterCloud Home AJAX — READ-ONLY final activation preflight.
# Fedora usage: ssh -T -p 1122 admin1@ROUTER 'sh -s' < scripts/routercloud-home-final-check.sh
# No writes, no restarts, no config/secret printing.
set -eu

echo '=== ROUTERCLOUD FINAL ACTIVATION PREFLIGHT ==='

CONF=/opt/etc/dufs-personal-cloud.yaml
INIT=/opt/etc/init.d/S67routercloud
BACKUP=/opt/var/backups/routercloud-home-ajax-20261012
OLD_SHA=d5052ea33917bad9314a49792bc555dd2e7ce2a3f2532aaff3b83c23e4c593b4
NEW_SHA=90171cdb676cb39de41a8e74384ac509294c617ae31a0b06735f5f7f527bcb0c
PREV_REV=503161dd5bee21ac

fail() {
    echo "FINAL_PREFLIGHT=STOP reason=$1"
    exit 1
}

[ -r "$CONF" ] || fail YAML_UNREADABLE
[ -f "$INIT" ] || fail SERVICE_SCRIPT_NOT_FOUND

ASSETS="$(awk '
    /^[[:space:]]*assets:[[:space:]]*/ {
        sub(/^[[:space:]]*assets:[[:space:]]*/, "")
        gsub(/"/, "")
        sub(/[[:space:]]*$/, "")
        print
        exit
    }' "$CONF")"

case "$ASSETS" in
    /opt/share/*) ;;
    *) fail ASSETS_PATH_UNEXPECTED ;;
esac

# Pin to the *observed* live assets folder; abort on subsequent YAML drift.
[ "$ASSETS" = /opt/share/routercloud-password-recovery-20261003-163712 ] ||
    fail ACTIVE_ASSET_DIRECTORY_CHANGED

[ -d "$ASSETS" ] && [ ! -L "$ASSETS" ] || fail ASSET_DIR_INVALID
[ -d "$BACKUP" ] && [ ! -L "$BACKUP" ] || fail BACKUP_DIR_INVALID

for path in \
    "$ASSETS/index.js" \
    "$ASSETS/index.html" \
    "$ASSETS/index.css" \
    "$ASSETS/favicon.ico" \
    "$BACKUP/index.js" \
    "$BACKUP/index.candidate.js"; do
    [ -f "$path" ] && [ -r "$path" ] && [ ! -L "$path" ] ||
        fail MISSING_UNREADABLE_OR_SYMLINK_FILE
done

getsha() { sha256sum "$1" | awk '{print $1}'; }
[ "$(getsha "$ASSETS/index.js")" = "$OLD_SHA" ] ||
    fail LIVE_INDEX_CHANGED
[ "$(getsha "$BACKUP/index.js")" = "$OLD_SHA" ] ||
    fail BACKUP_HASH_CHANGED
[ "$(getsha "$BACKUP/index.candidate.js")" = "$NEW_SHA" ] ||
    fail STAGED_HASH_CHANGED
[ "$(wc -c < "$BACKUP/index.candidate.js" | tr -d '[:space:]')" = 92809 ] ||
    fail STAGED_SIZE_CHANGED

for needle in wolne łącznie niedostępne ROUTERCLOUD_HOME_AJAX_V1; do
    grep -Fq "$needle" "$BACKUP/index.candidate.js" ||
        fail CANDIDATE_FEATURE_MARKER_MISSING
done

revision() {
    mode="$1"
    (
        cd "$ASSETS" || exit 1
        for name in index.html index.css index.js favicon.ico; do
            printf '%s' "$name"
            if [ "$name" = index.js ] && [ "$mode" = staged ]; then
                cat "$BACKUP/index.candidate.js"
            else
                cat "$name"
            fi
        done
    ) | sha256sum | awk '{print substr($1,1,16)}'
}
LIVE_REV="$(revision live)"
NEW_REV="$(revision staged)"
[ "$LIVE_REV" = "$PREV_REV" ] || fail LIVE_REVISION_CHANGED
[ "$NEW_REV" != "$LIVE_REV" ] || fail CANDIDATE_REVISION_NOT_CHANGED

echo 'ASSET_SOURCE=PINNED'
echo 'LIVE_INDEX_INTEGRITY=PASS'
echo 'ROLLBACK_INTEGRITY=PASS'
echo 'STAGED_CANDIDATE_INTEGRITY=PASS'
echo 'STAGED_FEATURE_MARKERS=PASS'
echo "LIVE_ASSETS_REV=$LIVE_REV"
echo "EXPECTED_CANDIDATE_ASSETS_REV=$NEW_REV"
echo 'ROUTERCLOUD_INIT=FOUND'
echo 'ACTIVE_FILES_MODIFIED=NO'
echo 'ROUTERCLOUD_RESTARTED=NO'
echo 'FINAL_PREFLIGHT=PASS'
