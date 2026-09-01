#!/bin/sh

set -u

ARCHIVE="${1:-}"
MODE="${2:---dry-run}"

usage() {
    echo "Usage: $0 BACKUP.tar.gz [--dry-run|--apply]"
}

[ -n "$ARCHIVE" ] || { usage; exit 2; }
[ -f "$ARCHIVE" ] || { echo "ERROR: backup not found" >&2; exit 1; }
case "$MODE" in --dry-run|--apply) ;; *) usage; exit 2 ;; esac

TMP_DIR="$(mktemp -d /tmp/asus-edge-restore.XXXXXX)" || exit 1
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

tar -tzf "$ARCHIVE" | grep -Eq '(^|/)\.\.?(/|$)' && { echo "ERROR: unsafe archive path" >&2; exit 1; }
if tar -tvzf "$ARCHIVE" | awk 'substr($1,1,1) == "l" || substr($1,1,1) == "h" { found=1 } END { exit !found }'; then
    echo "ERROR: symbolic/hard links are not accepted in backups" >&2
    exit 1
fi
tar -xzf "$ARCHIVE" -C "$TMP_DIR" || exit 1
ROOT="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
[ -n "$ROOT" ] || { echo "ERROR: invalid backup" >&2; exit 1; }
(cd "$ROOT" && sha256sum -c SHA256SUMS) || exit 1

echo "Verified backup contents:"
find "$ROOT" -type f | sed "s#^$ROOT/##" | sort

[ "$MODE" = "--apply" ] || { echo "Dry-run only. Re-run with --apply to restore."; exit 0; }
[ "$(id -u)" = "0" ] || { echo "ERROR: run as root" >&2; exit 1; }

[ -d "$ROOT/jffs" ] && cp -R "$ROOT/jffs/." /jffs/
[ -d "$ROOT/opt" ] && cp -R "$ROOT/opt/." /opt/
echo "Restore completed. Reboot or restart services after reviewing files."
