#!/bin/sh
# RouterCloud Home AJAX: manual UI-only rollback after failed browser acceptance.
# Fedora: ssh -T -p 1122 admin1@192.168.50.1 'sh -s' < scripts/routercloud-home-rollback.sh
set -eu

echo '=== ROUTERCLOUD HOME AJAX ROLLBACK ==='

CONF=/opt/etc/dufs-personal-cloud.yaml
INIT=/opt/etc/init.d/S67routercloud
ASSET_DIR=/opt/share/routercloud-password-recovery-20261003-163712
LIVE="$ASSET_DIR/index.js"
BACKUP_DIR=/opt/var/backups/routercloud-home-ajax-20261012
BACKUP="$BACKUP_DIR/index.js"
OLD_SHA=d5052ea33917bad9314a49792bc555dd2e7ce2a3f2532aaff3b83c23e4c593b4
NEW_SHA=90171cdb676cb39de41a8e74384ac509294c617ae31a0b06735f5f7f527bcb0c
OLD_REV=503161dd5bee21ac
NEW_REV=a6b8ba062e194c1e

stop() { echo "ROLLBACK=STOP reason=$1" >&2; exit 1; }
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

[ "$(id -u)" = 0 ] || stop NOT_ROOT
[ -r "$CONF" ] || stop YAML_UNREADABLE
[ -x "$INIT" ] || stop ROUTERCLOUD_INIT_NOT_EXECUTABLE
[ -d "$ASSET_DIR" ] && [ ! -L "$ASSET_DIR" ] || stop ASSETS_INVALID
[ -d "$BACKUP_DIR" ] && [ ! -L "$BACKUP_DIR" ] || stop BACKUP_DIR_INVALID
CONFIGURED="$(awk '
    /^[[:space:]]*assets:[[:space:]]*/ {
        sub(/^[[:space:]]*assets:[[:space:]]*/, "")
        gsub(/"/, "")
        sub(/[[:space:]]*$/, "")
        print
        exit
    }' "$CONF")"
[ "$CONFIGURED" = "$ASSET_DIR" ] || stop YAML_ASSETS_CHANGED

for file in "$LIVE" "$BACKUP" \
    "$ASSET_DIR/index.html" "$ASSET_DIR/index.css" \
    "$ASSET_DIR/favicon.ico"; do
    [ -f "$file" ] && [ -r "$file" ] && [ ! -L "$file" ] ||
        stop REQUIRED_FILE_INVALID
done
[ "$(getsha "$BACKUP")" = "$OLD_SHA" ] || stop BACKUP_SHA_CHANGED

CURRENT="$(getsha "$LIVE")"
if [ "$CURRENT" = "$OLD_SHA" ]; then
    echo 'ROLLBACK_ALREADY_AT_ORIGINAL_SHA=YES'
    echo "CURRENT_ASSETS_REV=$(revision)"
    echo 'ROUTERCLOUD_RESTARTED=NO'
    exit 0
fi
[ "$CURRENT" = "$NEW_SHA" ] || stop UNKNOWN_ACTIVE_VERSION
[ "$(revision)" = "$NEW_REV" ] || stop UNKNOWN_ACTIVE_ASSET_REVISION

umask 077
TEMP="$(mktemp "$ASSET_DIR/.index.js.routercloud-rollback-XXXXXX")"
trap 'rm -f "$TEMP"' 0 1 2 15

cp "$BACKUP" "$TEMP"
[ "$(getsha "$TEMP")" = "$OLD_SHA" ] || stop RESTORE_TEMP_HASH
chown 0:0 "$TEMP"
chmod 0644 "$TEMP"
mv -f "$TEMP" "$LIVE"
TEMP=''

[ "$(getsha "$LIVE")" = "$OLD_SHA" ] || stop RESTORE_LIVE_HASH

echo 'RESTORED_LIVE_INDEX=PASS'
echo 'RESTARTING_ROUTERCLOUD=YES'
if ! "$INIT" restart; then
    echo 'ROUTERCLOUD_RESTART_COMMAND=FAIL' >&2
    echo 'ROLLBACK_REQUIRES_OPERATOR_RECOVERY=YES' >&2
    exit 1
fi

[ "$(revision)" = "$OLD_REV" ] || stop RESTORED_REVISION_MISMATCH

echo 'ROUTERCLOUD_RESTART_COMMAND=PASS'
echo "RESTORED_ASSETS_REV=$OLD_REV"
echo 'ROLLBACK=PASS'
echo 'FEDORA_HTTPS_BROWSER_ACCEPTANCE=PENDING'
echo '=== ROLLBACK COMPLETE ==='
