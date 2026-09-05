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

tar -tzf "$ARCHIVE" >"$TMP_DIR/paths" || exit 1
if ! awk '
    !/^[A-Za-z0-9_.$\/-]+$/ || /^\// || /(^|\/)\.\.?($|\/)/ { exit 1 }
    {
        sub(/\/$/, "")
        if (seen[$0]++) exit 1
        split($0, parts, "/")
        if (root != "" && root != parts[1]) exit 1
        root=parts[1]
    }
    END { if (root == "") exit 1 }
' "$TMP_DIR/paths"; then
    echo "ERROR: unsafe, duplicate, or multiple-root archive paths" >&2
    exit 1
fi
tar -tvzf "$ARCHIVE" >"$TMP_DIR/types" || exit 1
if ! awk 'substr($1,1,1) != "-" && substr($1,1,1) != "d" { exit 1 }' "$TMP_DIR/types"; then
    echo "ERROR: only regular files and directories are accepted in backups" >&2
    exit 1
fi
mkdir "$TMP_DIR/payload" || exit 1
tar -xzf "$ARCHIVE" -C "$TMP_DIR/payload" || exit 1
ROOT="$(find "$TMP_DIR/payload" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
[ -n "$ROOT" ] || { echo "ERROR: invalid backup" >&2; exit 1; }
[ -f "$ROOT/SHA256SUMS" ] || { echo "ERROR: missing manifest" >&2; exit 1; }

# Check manifest paths BEFORE sha256sum opens them, and require an exact
# one-to-one match with payload files. Hashes detect corruption, not authenticity.
if ! awk '
    {
        hash=substr($0,1,64); separator=substr($0,65,2); path=substr($0,67)
        if (length(hash) != 64 || hash ~ /[^0-9a-fA-F]/) exit 1
        if (separator != "  " && separator != " *") exit 1
        sub(/^\.\//, "", path)
        if (path !~ /^[A-Za-z0-9_.$\/-]+$/ || path ~ /^\// ||
            path ~ /(^|\/)\.\.?($|\/)/ || path == "SHA256SUMS" || seen[path]++) exit 1
        print path
    }
' "$ROOT/SHA256SUMS" >"$TMP_DIR/manifest-paths"; then
    echo "ERROR: invalid manifest paths or records" >&2
    exit 1
fi
(cd "$ROOT" && find . -type f ! -path './SHA256SUMS' | sed 's#^\./##' | sort) >"$TMP_DIR/payload-paths" || exit 1
sort "$TMP_DIR/manifest-paths" >"$TMP_DIR/sorted-manifest" || exit 1
if ! cmp -s "$TMP_DIR/payload-paths" "$TMP_DIR/sorted-manifest"; then
    echo "ERROR: manifest must cover every payload file exactly once" >&2
    exit 1
fi
(cd "$ROOT" && sha256sum_run -c SHA256SUMS) || exit 1

echo "Verified backup contents:"
find "$ROOT" -type f | sed "s#^$ROOT/##" | sort

[ "$MODE" = "--apply" ] || { echo "Dry-run only. Re-run with --apply to restore."; exit 0; }
uid="$(current_uid)" || { echo "ERROR: cannot determine current user" >&2; exit 1; }
[ "$uid" = "0" ] || { echo "ERROR: run as root" >&2; exit 1; }

for destination in jffs opt; do
    if [ -d "$ROOT/$destination" ]; then
        cp -Rp "$ROOT/$destination/." "/$destination/" || {
            echo "ERROR: restore copy failed for /$destination; restore may be partial" >&2
            exit 1
        }
    fi
done
echo "Restore completed. Reboot or restart services after reviewing files."
