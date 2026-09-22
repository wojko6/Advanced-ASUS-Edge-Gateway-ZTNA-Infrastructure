#!/bin/sh

set -eu

LOG_ROOT="${ASUS_EDGE_ROUTER_LOG_ROOT:-/opt/var/log/asus-edge}"
MAX_AGE_DAYS="${ASUS_EDGE_ROUTER_LOG_MAX_AGE_DAYS:-30}"
MAX_TOTAL_KB="${ASUS_EDGE_ROUTER_LOG_MAX_KB:-65536}"
TODAY_LOG="$(date +%Y-%m-%d).log"
MODE="${1:---dry-run}"

if [ -n "${ASUS_EDGE_TEST_ROOT:-}" ]; then
    case "$LOG_ROOT" in
        "$ASUS_EDGE_TEST_ROOT"|"$ASUS_EDGE_TEST_ROOT"/*) ;;
        *) echo "ERROR: test log root escaped ASUS_EDGE_TEST_ROOT" >&2; exit 2 ;;
    esac
else
    case "$LOG_ROOT" in
        /opt/var/log/asus-edge|/opt/var/log/asus-edge/*) ;;
        *)
            echo "ERROR: router log root must stay below /opt/var/log/asus-edge" >&2
            exit 2
            ;;
    esac
fi
[ ! -L "$LOG_ROOT" ] || {
    echo "ERROR: refusing symlink router log root" >&2
    exit 2
}

for value in "$MAX_AGE_DAYS" "$MAX_TOTAL_KB"; do
    case "$value" in
        ''|*[!0-9]*) echo "ERROR: retention limits must be positive integers" >&2; exit 2 ;;
    esac
    [ "$value" -gt 0 ] || { echo "ERROR: retention limits must be greater than zero" >&2; exit 2; }
done

case "$MODE" in --dry-run|--apply) ;; *) echo "Usage: $0 [--dry-run|--apply]" >&2; exit 2 ;; esac
[ -d "$LOG_ROOT" ] || exit 0

managed_file() {
    file_path="$1"
    [ -f "$file_path" ] || return 1
    [ ! -L "$file_path" ] || return 1
    file_name="${file_path##*/}"
    case "$file_name" in
        [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].log|        [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].log.gz) return 0 ;;
        *) return 1 ;;
    esac
}

managed_size_kb() {
    total_kb=0
    for file_path in "$LOG_ROOT"/*; do
        managed_file "$file_path" || continue
        file_kb="$(du -k "$file_path" 2>/dev/null | awk 'NR==1 {print $1}')"
        case "$file_kb" in ''|*[!0-9]*) continue ;; esac
        total_kb=$((total_kb + file_kb))
    done
    printf '%s\n' "$total_kb"
}

oldest_removable_file() {
    oldest_path=""
    oldest_epoch=""
    for file_path in "$LOG_ROOT"/*; do
        managed_file "$file_path" || continue
        file_name="${file_path##*/}"
        [ "$file_name" != "$TODAY_LOG" ] || continue
        file_epoch="$(stat -c %Y "$file_path" 2>/dev/null)" || continue
        case "$file_epoch" in ''|*[!0-9]*) continue ;; esac
        if [ -z "$oldest_epoch" ] || [ "$file_epoch" -lt "$oldest_epoch" ]; then
            oldest_epoch="$file_epoch"
            oldest_path="$file_path"
        fi
    done
    [ -n "$oldest_path" ] || return 1
    printf '%s\n' "$oldest_path"
}

echo "=== AGE-ELIGIBLE MANAGED ROUTER LOGS ==="
for file_path in "$LOG_ROOT"/*; do
    managed_file "$file_path" || continue
    file_name="${file_path##*/}"
    [ "$file_name" != "$TODAY_LOG" ] || continue
    if find "$file_path" -type f -mtime "+$MAX_AGE_DAYS" -print 2>/dev/null | grep -q .; then
        printf '%s\n' "$file_path"
        [ "$MODE" = "--dry-run" ] || rm -f "$file_path"
    fi
done

current_kb="$(managed_size_kb)"
echo "Managed router log usage: ${current_kb} KiB / ${MAX_TOTAL_KB} KiB"

if [ "$MODE" = "--dry-run" ]; then
    exit 0
fi

while [ "$current_kb" -gt "$MAX_TOTAL_KB" ]; do
    oldest="$(oldest_removable_file)" || {
        echo "ERROR: managed log usage exceeds limit but no safe removable file remains" >&2
        exit 1
    }
    echo "Removing oldest managed router log to enforce size cap: $oldest"
    rm -f "$oldest" || exit 1
    current_kb="$(managed_size_kb)"
done

exit 0
