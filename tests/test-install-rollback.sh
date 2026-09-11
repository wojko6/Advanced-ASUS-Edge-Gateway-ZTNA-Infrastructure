#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
TMPROOT="$(mktemp -d)"
trap 'rm -rf "$TMPROOT"' EXIT HUP INT TERM

mkdir -p "$TMPROOT/jffs/scripts" "$TMPROOT/jffs/configs"
mkdir -p "$TMPROOT/jffs/addons/asus-edge"

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

EDGE_TEST_ROOT="$TMPROOT" sh "$TMPROOT/repo/scripts/install.sh"

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

if EDGE_TEST_ROOT="$TMPROOT" sh "$TMPROOT/repo/scripts/install.sh"; then
    echo "FAIL: installation unexpectedly succeeded"
    exit 1
fi

grep -q 'legacy' "$TMPROOT/jffs/scripts/wan-event"
echo "PASS: rollback restored previous hook"
