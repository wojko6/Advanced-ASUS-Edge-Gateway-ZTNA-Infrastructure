#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"

CLIENT="$REPO_DIR/scripts/routercloud-sync.sh"
WRAPPER="$REPO_DIR/router/scripts/personal-cloud-rsync"
SERVICE="$REPO_DIR/config/systemd/routercloud-sync.service"
TIMER="$REPO_DIR/config/systemd/routercloud-sync.timer"
PATH_UNIT="$REPO_DIR/config/systemd/routercloud-sync.path"

for file in "$CLIENT" "$WRAPPER" "$SERVICE" "$TIMER" "$PATH_UNIT"; do
    [ -s "$file" ] || {
        echo "FAIL: missing Personal Cloud artifact: $file" >&2
        exit 1
    }
done

bash -n "$CLIENT"
sh -n "$WRAPPER"

if grep -F -- '--delete' "$CLIENT" >/dev/null; then
    echo "FAIL: RouterCloud v1 client must not use --delete" >&2
    exit 1
fi

for guard in \
    '/usr/bin/rsync -rtv' \
    '--rsync-path=/opt/bin/rsync' \
    '-F /dev/null' \
    'IdentityFile=none' \
    'IdentitiesOnly=yes' \
    'IdentityAgent=none' \
    'BatchMode=yes' \
    'PasswordAuthentication=no' \
    'KbdInteractiveAuthentication=no' \
    'PreferredAuthentications=publickey' \
    'StrictHostKeyChecking=yes' \
    'ConnectTimeout=10' \
    '/tmp/mnt/ROUTER_DATA/RouterCloud/' \
    'flock -n 9' \
    'LAST_RESULT=' \
    'LAST_DURATION_SECONDS='
do
    grep -F -- "$guard" "$CLIENT" >/dev/null || {
        echo "FAIL: client guard missing: $guard" >&2
        exit 1
    }
done

for guard in \
    'PATH="/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin"' \
    'LIVE="/opt/bin/rsync --server -vtre.iLsfxCIvu . /tmp/mnt/ROUTER_DATA/RouterCloud/"' \
    'DRY="/opt/bin/rsync --server -vntre.iLsfxCIvu . /tmp/mnt/ROUTER_DATA/RouterCloud/"' \
    'Personal Cloud: command denied' \
    'exit 126'
do
    grep -F -- "$guard" "$WRAPPER" >/dev/null || {
        echo "FAIL: server restriction missing: $guard" >&2
        exit 1
    }
done

if denied_output="$(SSH_ORIGINAL_COMMAND=id sh "$WRAPPER" 2>&1)"; then
    echo "FAIL: restricted wrapper accepted an arbitrary command" >&2
    exit 1
else
    denied_rc=$?
fi

[ "$denied_rc" -eq 126 ] || {
    echo "FAIL: arbitrary command returned rc=$denied_rc instead of 126" >&2
    exit 1
}

printf '%s\n' "$denied_output" | grep -F 'Personal Cloud: command denied' >/dev/null || {
    echo "FAIL: arbitrary command did not return the expected denial" >&2
    exit 1
}

grep -F 'ExecStart=%h/.local/bin/routercloud-sync' "$SERVICE" >/dev/null
grep -F 'UMask=0077' "$SERVICE" >/dev/null
grep -F 'NoNewPrivileges=yes' "$SERVICE" >/dev/null
grep -F 'OnUnitActiveSec=5min' "$TIMER" >/dev/null
grep -F 'Persistent=true' "$TIMER" >/dev/null
grep -F 'PathChanged=%h/RouterCloud' "$PATH_UNIT" >/dev/null

echo "PASS: Personal Cloud static policy checks"
