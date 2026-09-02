#!/bin/sh

set -u

PATH="/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin"

current_uid() {
    while read -r status_key status_uid _; do
        if [ "$status_key" = "Uid:" ]; then
            printf '%s\n' "$status_uid"
            return 0
        fi
    done </proc/self/status
    return 1
}

secure_temp_dir() {
    temp_prefix="$1"
    temp_counter=0
    while [ "$temp_counter" -lt 100 ]; do
        temp_candidate="$temp_prefix.$.$temp_counter"
        if (umask 077 && mkdir "$temp_candidate") 2>/dev/null; then
            printf '%s\n' "$temp_candidate"
            return 0
        fi
        temp_counter=$((temp_counter + 1))
    done
    return 1
}

sha256sum_run() {
    for sum_bin in /opt/bin/sha256sum /opt/sbin/sha256sum /usr/bin/sha256sum /usr/sbin/sha256sum /bin/sha256sum /sbin/sha256sum; do
        [ -x "$sum_bin" ] && { "$sum_bin" "$@"; return; }
    done
    if [ -x /bin/busybox ] && /bin/busybox sha256sum /dev/null >/dev/null 2>&1; then
        /bin/busybox sha256sum "$@"
        return
    fi
    echo "ERROR: sha256sum unavailable" >&2
    return 1
}

ARCHIVE="${1:-}"
MODE="${2:---dry-run}"

usage() {
    echo "Usage: $0 BACKUP.tar.gz [--dry-run|--apply]"
}

[ -n "$ARCHIVE" ] || { usage; exit 2; }
[ -f "$ARCHIVE" ] || { echo "ERROR: backup not found" >&2; exit 1; }
case "$MODE" in --dry-run|--apply) ;; *) usage; exit 2 ;; esac

TMP_DIR="$(secure_temp_dir /tmp/asus-edge-restore)" || {
    echo "ERROR: cannot create private restore workspace" >&2
    exit 1
}
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

tar -tzf "$ARCHIVE" | grep -Eq '(^|/)\.\.?(/|$)' && { echo "ERROR: unsafe archive path" >&2; exit 1; }
if tar -tvzf "$ARCHIVE" | awk 'substr($1,1,1) == "l" || substr($1,1,1) == "h" { found=1 } END { exit !found }'; then
    echo "ERROR: symbolic/hard links are not accepted in backups" >&2
    exit 1
fi
tar -xzf "$ARCHIVE" -C "$TMP_DIR" || exit 1
ROOT="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
[ -n "$ROOT" ] || { echo "ERROR: invalid backup" >&2; exit 1; }
(cd "$ROOT" && sha256sum_run -c SHA256SUMS) || exit 1

echo "Verified backup contents:"
find "$ROOT" -type f | sed "s#^$ROOT/##" | sort

[ "$MODE" = "--apply" ] || { echo "Dry-run only. Re-run with --apply to restore."; exit 0; }
uid="$(current_uid)" || { echo "ERROR: cannot determine current user" >&2; exit 1; }
[ "$uid" = "0" ] || { echo "ERROR: run as root" >&2; exit 1; }

[ -d "$ROOT/jffs" ] && cp -R "$ROOT/jffs/." /jffs/
[ -d "$ROOT/opt" ] && cp -R "$ROOT/opt/." /opt/
echo "Restore completed. Reboot or restart services after reviewing files."
