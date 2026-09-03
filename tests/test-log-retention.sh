#!/bin/sh

set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
RETENTION_SCRIPT="$REPO_DIR/scripts/asus-edge-log-retention.sh"
TEMP_DIR="$(mktemp -d)"
LOG_ROOT="$TEMP_DIR/logs"

cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$LOG_ROOT/router"
TODAY_LOG="$LOG_ROOT/router/$(date +%Y-%m-%d).log"
OLD_LOG="$LOG_ROOT/router/old.log"
EXPIRED_LOG="$LOG_ROOT/router/expired.log.gz"

printf '%s\n' 'active log' >"$TODAY_LOG"
printf '%s\n' 'compress me' >"$OLD_LOG"
printf '%s\n' 'expire me' | gzip >"$EXPIRED_LOG"

touch -d '2 days ago' "$TODAY_LOG" "$OLD_LOG"
touch -d '31 days ago' "$EXPIRED_LOG"

DRY_RUN_OUTPUT="$(ASUS_EDGE_LOG_ROOT="$LOG_ROOT" "$RETENTION_SCRIPT" --dry-run)"
printf '%s\n' "$DRY_RUN_OUTPUT" | grep -F "$OLD_LOG" >/dev/null
printf '%s\n' "$DRY_RUN_OUTPUT" | grep -F "$EXPIRED_LOG" >/dev/null

ASUS_EDGE_LOG_ROOT="$LOG_ROOT" "$RETENTION_SCRIPT" --apply >/dev/null

test -f "$TODAY_LOG"
test ! -e "$OLD_LOG"
test -f "$OLD_LOG.gz"
gzip -t "$OLD_LOG.gz"
test ! -e "$EXPIRED_LOG"

if ASUS_EDGE_LOG_ROOT='/' "$RETENTION_SCRIPT" --dry-run >/dev/null 2>&1; then
    echo "FAIL: filesystem root was accepted" >&2
    exit 1
fi

if ASUS_EDGE_LOG_ROOT='relative/path' "$RETENTION_SCRIPT" --dry-run >/dev/null 2>&1; then
    echo "FAIL: relative log root was accepted" >&2
    exit 1
fi

echo "PASS: collector log retention"
