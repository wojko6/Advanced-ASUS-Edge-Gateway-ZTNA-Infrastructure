#!/usr/bin/bash
set -u
umask 077

STATE_DIR="${ROUTERCLOUD_BACKUP_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/routercloud-backup}"
STATE="${ROUTERCLOUD_BACKUP_STATUS_FILE:-$STATE_DIR/status.env}"

ROUTERCLOUD_HOST="${ROUTERCLOUD_BACKUP_HOST:-192.168.50.1}"
ROUTERCLOUD_USER="${ROUTERCLOUD_BACKUP_USER:-admin1}"
ROUTERCLOUD_SSH_PORT="${ROUTERCLOUD_BACKUP_SSH_PORT:-1122}"

KEY="${ROUTERCLOUD_STATUS_KEY:-$HOME/.ssh/id_ed25519_routercloud_status}"
REMOTE_COMMAND="routercloud-status-publish"

TMP="$(mktemp)"

cleanup() {
    rm -f "$TMP"
}

trap cleanup EXIT HUP INT TERM

if [ ! -r "$STATE" ]; then
    exit 66
fi

if [ ! -r "$KEY" ]; then
    exit 66
fi

STATE="$STATE" TMP="$TMP" python3 <<'PY'
from pathlib import Path
from datetime import datetime
import json
import os
import subprocess

values = {}

for line in Path(
    os.environ["STATE"]
).read_text(
    encoding="utf-8",
    errors="strict",
).splitlines():
    if "=" not in line:
        continue

    key, value = line.split("=", 1)
    values[key] = value

try:
    next_run = subprocess.check_output(
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
except Exception:
    next_run = ""

payload = {
    "schema": 1,
    "result":
        values.get("LAST_RESULT", ""),
    "rc":
        int(values.get("LAST_RC", "-1")),
    "stage":
        values.get("LAST_STAGE", ""),
    "start":
        values.get("LAST_START", ""),
    "end":
        values.get("LAST_END", ""),
    "duration_seconds":
        int(
            values.get(
                "LAST_DURATION_SECONDS",
                "0",
            )
        ),
    "next_run":
        next_run,
    "generated_at":
        datetime.now()
        .astimezone()
        .isoformat(
            timespec="seconds"
        ),
}

Path(
    os.environ["TMP"]
).write_text(
    json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ) + "\n",
    encoding="utf-8",
)
PY

chmod 0600 "$TMP"

/usr/bin/ssh \
    -F /dev/null \
    -o IdentityFile=none \
    -i "$KEY" \
    -o IdentitiesOnly=yes \
    -o IdentityAgent=none \
    -o BatchMode=yes \
    -o PasswordAuthentication=no \
    -o KbdInteractiveAuthentication=no \
    -o PreferredAuthentications=publickey \
    -o StrictHostKeyChecking=yes \
    -o ConnectTimeout=10 \
    -p "$ROUTERCLOUD_SSH_PORT" \
    "${ROUTERCLOUD_USER}@${ROUTERCLOUD_HOST}" \
    "$REMOTE_COMMAND" \
    < "$TMP"

RC=$?
exit "$RC"
