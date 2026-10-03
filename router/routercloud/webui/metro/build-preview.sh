#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREVIEW="/tmp/routercloud-metro-preview"
PORT="8765"
PIDFILE="/tmp/routercloud-metro-preview.pid"
LOGFILE="/tmp/routercloud-metro-preview.log"

rm -rf "$PREVIEW"
mkdir -p "$PREVIEW"

cp "$HERE/index.html" "$PREVIEW/index.html"
cp "$HERE/index.css" "$PREVIEW/index.css"
cp "$HERE/index.js" "$PREVIEW/index.js"
cp "$HERE/favicon.ico" "$PREVIEW/favicon.ico"
cp "$HERE/login.html" "$PREVIEW/login.html"
cp "$HERE/login.css" "$PREVIEW/login.css"
cp "$HERE/login.js" "$PREVIEW/login.js"

python3 - <<'PYLOGIN'
from pathlib import Path

path = Path("/tmp/routercloud-metro-preview/login.html")
html = path.read_text(encoding="utf-8")

html = html.replace(
    'method="post"\n        action="/__routercloud/login"',
    'method="post"\n        action="#"\n        onsubmit="event.preventDefault()"'
)

html = html.replace(
    'href="/__routercloud/login.css"',
    'href="login.css"'
)

# Preview nie udostępnia produkcyjnej ścieżki DUFS.
# Używamy lokalnego favicon.ico kopiowanego wyżej.
html = html.replace(
    '/__dufs_v0.46.0__/favicon.ico?v=routercloud-brand-v1',
    'favicon.ico?v=preview'
)

html = html.replace(
    '<script src="/__routercloud/login.js" defer></script>',
    ''
)

path.write_text(html, encoding="utf-8")
PYLOGIN

python3 - <<'PY'
from pathlib import Path
from datetime import datetime, timezone
import base64
import json
import subprocess

path = Path("/tmp/routercloud-metro-preview/index.html")

def ts(year, month, day, hour, minute):
    return int(
        datetime(
            year, month, day, hour, minute,
            tzinfo=timezone.utc
        ).timestamp() * 1000
    )

GiB = 1024 ** 3
MiB = 1024 ** 2
KiB = 1024

# ROUTERCLOUD_BACKUP_TILE_V1
backup_status = None

status_path = (
    Path.home()
    / ".local"
    / "state"
    / "routercloud-backup"
    / "status.env"
)

if status_path.is_file():
    values = {}

    for line in status_path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key] = value

    next_run = ""

    try:
        raw_next = subprocess.check_output(
            [
                "systemctl",
                "--user",
                "show",
                "routercloud-backup.timer",
                "-p",
                "NextElapseUSecRealtime",
                "--value",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

        if raw_next:
            next_run = raw_next

    except Exception:
        pass

    backup_status = {
        "result":
            values.get("LAST_RESULT", ""),
        "rc":
            values.get("LAST_RC", ""),
        "stage":
            values.get("LAST_STAGE", ""),
        "start":
            values.get("LAST_START", ""),
        "end":
            values.get("LAST_END", ""),
        "duration_seconds":
            values.get(
                "LAST_DURATION_SECONDS",
                "",
            ),
        "next_run":
            next_run,
    }

data = {
    "href": "/",
    "uri_prefix": "/",
    "kind": "Index",

    "paths": [
        {
            "path_type": "Dir",
            "name": "api-test",
            "mtime": ts(2026, 10, 2, 10, 32),
            "size": 1,
        },
        {
            "path_type": "Dir",
            "name": "Testowy",
            "mtime": ts(2026, 10, 2, 11, 46),
            "size": 1,
        },
        {
            "path_type": "Dir",
            "name": "Backupy",
            "mtime": ts(2026, 10, 2, 9, 15),
            "size": 14,
        },
        {
            "path_type": "Dir",
            "name": "Logi",
            "mtime": ts(2026, 10, 2, 8, 55),
            "size": 8,
        },
        {
            "path_type": "File",
            "name": "routercloud-notes.txt",
            "mtime": ts(2026, 10, 2, 11, 20),
            "size": 18 * KiB,
        },
        {
            "path_type": "File",
            "name": "network-audit.pdf",
            "mtime": ts(2026, 10, 1, 18, 40),
            "size": int(4.8 * MiB),
        },
        {
            "path_type": "File",
            "name": "backup-2026-10-02.tar.zst",
            "mtime": ts(2026, 10, 2, 7, 30),
            "size": int(1.2 * GiB),
        },
    ],

    "allow_upload": True,
    "allow_move": True,
    "allow_delete": False,
    "routercloud_allow_delete": True,
    "allow_search": True,
    "allow_archive": True,

    "auth": True,
    "user": "demo",
    "dir_exists": True,

    "storage": {
        "used": int(2.0 * GiB),
        "available": int(372.3 * GiB),
        "total": int(394.4 * GiB),
    },

    "editable": False,

    "backup_status": backup_status,
}

encoded = base64.b64encode(
    json.dumps(
        data,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
).decode("ascii")

html = path.read_text(encoding="utf-8")

html = html.replace("__ASSETS_PREFIX__", "")
html = html.replace("__ASSETS_REV__", "preview")
html = html.replace("__INDEX_DATA__", encoded)

preview_marker = (
    '<script>window.ROUTERCLOUD_PREVIEW = true;</script>\n'
)

script_pos = html.find("<script src=")

if (
    "window.ROUTERCLOUD_PREVIEW = true" not in html
    and script_pos != -1
):
    html = (
        html[:script_pos]
        + preview_marker
        + html[script_pos:]
    )

path.write_text(html, encoding="utf-8")
PY

if grep -RqE '__ASSETS_PREFIX__|__ASSETS_REV__|__INDEX_DATA__' "$PREVIEW"; then
    echo "ERROR: zostały placeholdery DUFS"
    exit 2
fi

if ! ss -ltnH | awk '{print $4}' | grep -q ":${PORT}$"; then
    nohup \
        python3 -m http.server "$PORT" \
        --bind 127.0.0.1 \
        --directory "$PREVIEW" \
        </dev/null \
        >"$LOGFILE" 2>&1 &

    echo $! > "$PIDFILE"
    sleep 1
fi

for file in index.html index.css index.js favicon.ico login.html login.css login.js; do
    code="$(
        curl -s \
            -o /dev/null \
            -w '%{http_code}' \
            "http://127.0.0.1:${PORT}/${file}"
    )"

    if [ "$code" != "200" ]; then
        echo "ERROR: $file HTTP=$code"
        exit 3
    fi
done

echo "PREVIEW_BUILD=PASS"
echo "PREVIEW_URL=http://127.0.0.1:${PORT}/"
