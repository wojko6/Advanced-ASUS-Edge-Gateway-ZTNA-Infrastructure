#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
SCRIPT="$REPO_DIR/scripts/healthcheck.sh"

for required in \
    ': "${EDGE_TS_AUTO_UPDATE:=false}"' \
    'tailscale_auto_update_apply()' \
    'ok "Tailscale automatic update application disabled"' \
    'fail "Tailscale automatic update application enabled"' \
    'fail "cannot verify Tailscale automatic update application state"'
do
    grep -F "$required" "$SCRIPT" >/dev/null || {
        echo "FAIL: missing healthcheck auto-update guard: $required" >&2
        exit 1
    }
done

grep -F 'EDGE_TS_AUTO_UPDATE="false"' \
    "$REPO_DIR/config/edge.conf.example" >/dev/null || {
        echo "FAIL: example configuration does not disable Tailscale auto-update" >&2
        exit 1
    }

echo "PASS: Tailscale automatic update policy is persistent and health-checked"
