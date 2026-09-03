#!/bin/sh

set -eu

LOG_ROOT="${ASUS_EDGE_LOG_ROOT:-/var/log/asus-edge}"
COMPRESS_AFTER_MINUTES="${ASUS_EDGE_COMPRESS_AFTER_MINUTES:-1440}"
DELETE_AFTER_MINUTES="${ASUS_EDGE_DELETE_AFTER_MINUTES:-43200}"
TODAY_LOG="$(date +%Y-%m-%d).log"

case "$LOG_ROOT" in
    /*) ;;
    *)
        echo "ERROR: log root must be an absolute path" >&2
        exit 2
        ;;
esac

if [ "$LOG_ROOT" = "/" ]; then
    echo "ERROR: refusing to use the filesystem root" >&2
    exit 2
fi

for value in "$COMPRESS_AFTER_MINUTES" "$DELETE_AFTER_MINUTES"; do
    case "$value" in
        ''|*[!0-9]*)
            echo "ERROR: retention values must be positive integers" >&2
            exit 2
            ;;
    esac
    if [ "$value" -le 0 ]; then
        echo "ERROR: retention values must be greater than zero" >&2
        exit 2
    fi
done

[ -d "$LOG_ROOT" ] || exit 0

case "${1:---dry-run}" in
    --dry-run)
        echo "=== FILES ELIGIBLE FOR COMPRESSION ==="
        find "$LOG_ROOT" \
            -xdev \
            -type f \
            -name '*.log' \
            ! -name "$TODAY_LOG" \
            -mmin "+$COMPRESS_AFTER_MINUTES" \
            -print

        echo "=== COMPRESSED FILES ELIGIBLE FOR DELETION ==="
        find "$LOG_ROOT" \
            -xdev \
            -type f \
            -name '*.log.gz' \
            -mmin "+$DELETE_AFTER_MINUTES" \
            -print
        ;;

    --apply)
        find "$LOG_ROOT" \
            -xdev \
            -type f \
            -name '*.log' \
            ! -name "$TODAY_LOG" \
            -mmin "+$COMPRESS_AFTER_MINUTES" \
            -print \
            -exec gzip -- {} \;

        find "$LOG_ROOT" \
            -xdev \
            -type f \
            -name '*.log.gz' \
            -mmin "+$DELETE_AFTER_MINUTES" \
            -print \
            -exec rm -f -- {} \;

        find "$LOG_ROOT" \
            -xdev \
            -depth \
            -mindepth 1 \
            -type d \
            -empty \
            -exec rmdir -- {} \; 2>/dev/null || true
        ;;

    *)
        echo "Usage: $0 [--dry-run|--apply]" >&2
        exit 2
        ;;
esac
