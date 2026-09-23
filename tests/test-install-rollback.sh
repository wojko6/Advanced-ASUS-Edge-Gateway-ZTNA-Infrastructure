#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
TMPROOT="$(mktemp -d)"
trap 'rm -rf "$TMPROOT"' EXIT HUP INT TERM

mkdir -p "$TMPROOT/jffs/scripts" "$TMPROOT/jffs/configs"
mkdir -p "$TMPROOT/jffs/addons/asus-edge"
mkdir -p "$TMPROOT/jffs/addons/asus-edge/backups"
for old_snapshot in \
    install-20260101-000001 \
    install-20260102-000001 \
    install-20260103-000001-103 \
    install-20260104-000001-104
do
    mkdir "$TMPROOT/jffs/addons/asus-edge/backups/$old_snapshot"
    printf '%s\n' "$old_snapshot" >"$TMPROOT/jffs/addons/asus-edge/backups/$old_snapshot/marker"
done

mkdir "$TMPROOT/jffs/addons/asus-edge/backups/install-manual-note"
mkdir "$TMPROOT/jffs/addons/asus-edge/backups/install-20260105-abcdef"
printf '%s\n' keep >"$TMPROOT/jffs/addons/asus-edge/backups/install-manual-note/marker"
printf '%s\n' keep >"$TMPROOT/jffs/addons/asus-edge/backups/install-20260105-abcdef/marker"

printf '%s\n' '#!/bin/sh' 'echo legacy' > "$TMPROOT/jffs/scripts/wan-event"
chmod +x "$TMPROOT/jffs/scripts/wan-event"

cp -a "$ROOT_DIR"/. "$TMPROOT/repo"
cp "$TMPROOT/repo/config/edge.conf.example" "$TMPROOT/repo/config/edge.conf"

python3 - <<'PY' "$TMPROOT/repo/scripts/install.sh"
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
s = s.replace('uid="$(current_uid)" || { echo "ERROR: cannot determine current user" >&2; exit 1; }\n[ "$uid" = "0" ] || { echo "ERROR: run as root" >&2; exit 1; }\n','uid=0\n')
p.write_text(s)
PY

managed_snapshot_count() {
    count=0
    for snapshot in "$TMPROOT/jffs/addons/asus-edge/backups"/install-*; do
        [ -d "$snapshot" ] || continue
        name="$(basename "$snapshot")"
        rest="${name#install-}"
        [ "$rest" != "$name" ] || continue
        date_part="${rest%%-*}"
        rest="${rest#*-}"
        [ "${#date_part}" -eq 8 ] || continue
        case "$date_part" in ''|*[!0-9]*) continue ;; esac
        case "$rest" in
            *-*)
                time_part="${rest%%-*}"
                suffix_part="${rest#*-}"
                [ -n "$suffix_part" ] || continue
                case "$suffix_part" in *[!0-9]*) continue ;; esac
                ;;
            *)
                time_part="$rest"
                ;;
        esac
        [ "${#time_part}" -eq 6 ] || continue
        case "$time_part" in ''|*[!0-9]*) continue ;; esac
        count=$((count + 1))
    done
    printf '%s\n' "$count"
}

EDGE_TEST_ROOT="$TMPROOT" EDGE_INSTALL_BACKUP_KEEP=3 sh "$TMPROOT/repo/scripts/install.sh"

[ "$(managed_snapshot_count)" -eq 3 ] || {
    echo "FAIL: installer snapshot retention expected 3 managed directories" >&2
    exit 1
}
[ ! -e "$TMPROOT/jffs/addons/asus-edge/backups/install-20260101-000001" ] || {
    echo "FAIL: oldest installer snapshot was not pruned" >&2
    exit 1
}
[ ! -e "$TMPROOT/jffs/addons/asus-edge/backups/install-20260102-000001" ] || {
    echo "FAIL: second-oldest installer snapshot was not pruned" >&2
    exit 1
}
[ -e "$TMPROOT/jffs/addons/asus-edge/backups/install-20260103-000001-103" ] || {
    echo "FAIL: recent installer snapshot was pruned too aggressively" >&2
    exit 1
}
[ -e "$TMPROOT/jffs/addons/asus-edge/backups/install-20260104-000001-104" ] || {
    echo "FAIL: newest historical installer snapshot was pruned too aggressively" >&2
    exit 1
}

[ -e "$TMPROOT/jffs/addons/asus-edge/backups/install-manual-note/marker" ] || {
    echo "FAIL: unmanaged install-like directory was removed" >&2
    exit 1
}
[ -e "$TMPROOT/jffs/addons/asus-edge/backups/install-20260105-abcdef/marker" ] || {
    echo "FAIL: malformed install-like directory was removed" >&2
    exit 1
}


test -x "$TMPROOT/jffs/scripts/wan-event"
test -x "$TMPROOT/jffs/addons/asus-edge/bin/wan-event"
test -x "$TMPROOT/jffs/addons/asus-edge/bin/wan-event-handler"

echo "PASS: install completed in isolated root"

python3 - <<'PY' "$TMPROOT/repo/scripts/install.sh"
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
needle = 'install_file "$REPO_DIR/router/scripts/wan-event-handler" "$ADDON_DIR/bin/wan-event-handler" 0755\n'
replacement = needle + 'exit 1\n'
s = s.replace(needle, replacement, 1)
p.write_text(s)
PY

if EDGE_TEST_ROOT="$TMPROOT" EDGE_INSTALL_BACKUP_KEEP=3 sh "$TMPROOT/repo/scripts/install.sh"; then
    echo "FAIL: installation unexpectedly succeeded"
    exit 1
fi

grep -q 'legacy' "$TMPROOT/jffs/scripts/wan-event"
[ "$(managed_snapshot_count)" -eq 3 ] || {
    echo "FAIL: failed install bypassed managed snapshot retention" >&2
    exit 1
}
echo "PASS: rollback restored previous hook and installer snapshot retention remained bounded"
