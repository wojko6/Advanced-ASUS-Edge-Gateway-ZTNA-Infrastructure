#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
SCRIPT="$ROOT_DIR/scripts/router-log-retention.sh"
TMPROOT="$(mktemp -d)"
trap 'rm -rf "$TMPROOT"' EXIT HUP INT TERM
LOGROOT="$TMPROOT/asus-edge"
mkdir -p "$LOGROOT"

TODAY="$(date +%Y-%m-%d).log"
printf 'current\n' >"$LOGROOT/$TODAY"
printf 'old\n' >"$LOGROOT/2026-01-01.log"
printf 'foreign\n' >"$LOGROOT/notes.txt"
printf 'outside\n' >"$TMPROOT/outside"
ln -s "$TMPROOT/outside" "$LOGROOT/2025-01-01.log"
touch -d '3 days ago' "$LOGROOT/2026-01-01.log"

ASUS_EDGE_ROUTER_LOG_ROOT="$LOGROOT" \
ASUS_EDGE_ROUTER_LOG_MAX_AGE_DAYS=1 \
ASUS_EDGE_ROUTER_LOG_MAX_KB=1024 \
sh "$SCRIPT" --apply >/dev/null

[ ! -e "$LOGROOT/2026-01-01.log" ]
[ -f "$LOGROOT/$TODAY" ]
[ -f "$LOGROOT/notes.txt" ]
[ -L "$LOGROOT/2025-01-01.log" ]
grep -qx outside "$TMPROOT/outside"
echo 'PASS: age retention removes only managed regular files and skips symlinks/foreign files'

rm -f "$LOGROOT/2025-01-01.log"
dd if=/dev/zero of="$LOGROOT/2026-02-01.log" bs=1024 count=8 status=none
sleep 1
dd if=/dev/zero of="$LOGROOT/2026-02-02.log" bs=1024 count=8 status=none

ASUS_EDGE_ROUTER_LOG_ROOT="$LOGROOT" \
ASUS_EDGE_ROUTER_LOG_MAX_AGE_DAYS=3650 \
ASUS_EDGE_ROUTER_LOG_MAX_KB=4 \
sh "$SCRIPT" --apply >/dev/null

[ ! -e "$LOGROOT/2026-02-01.log" ]
[ ! -e "$LOGROOT/2026-02-02.log" ]
[ -f "$LOGROOT/$TODAY" ]
[ -f "$LOGROOT/notes.txt" ]
echo 'PASS: size cap removes oldest managed logs without touching current/foreign files'

ASUS_EDGE_ROUTER_LOG_ROOT="$TMPROOT/missing/asus-edge" \
sh "$SCRIPT" --dry-run >/dev/null
echo 'PASS: missing router log directory is harmless'

if ASUS_EDGE_ROUTER_LOG_ROOT=/tmp sh "$SCRIPT" --dry-run >/dev/null 2>&1; then
    echo 'FAIL: unsafe router log root was accepted' >&2
    exit 1
fi
echo 'PASS: unsafe router log root rejected'
