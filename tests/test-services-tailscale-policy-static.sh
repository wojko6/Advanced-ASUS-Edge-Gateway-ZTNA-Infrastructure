#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
SCRIPT="$REPO_DIR/router/scripts/services-start"

[ -r "$SCRIPT" ] || { echo "FAIL: missing services-start" >&2; exit 1; }

grep -F 'if "$@" >/tmp/asus-edge-tailscale-up.log 2>&1; then' "$SCRIPT" >/dev/null || {
    echo "FAIL: tailscale up is not checked explicitly" >&2
    exit 1
}
grep -F 'log "ERROR: tailscale up failed; inspect /tmp/asus-edge-tailscale-up.log"' "$SCRIPT" >/dev/null || {
    echo "FAIL: tailscale up failure is not logged as ERROR" >&2
    exit 1
}
grep -F 'log "ERROR: Tailscale local API unavailable or node not ready"' "$SCRIPT" >/dev/null || {
    echo "FAIL: local API/not-ready path is not fatal" >&2
    exit 1
}
grep -F 'log "ERROR: tailscaled not installed"' "$SCRIPT" >/dev/null || {
    echo "FAIL: missing tailscaled is not treated as required-service failure" >&2
    exit 1
}

failure_assignments="$(grep -c 'startup_failed=1' "$SCRIPT")"
[ "$failure_assignments" -ge 5 ] || {
    echo "FAIL: required startup failures are not aggregated" >&2
    exit 1
}

grep -F 'if [ "$startup_failed" -ne 0 ]; then log "ERROR: required service startup failed"; exit 1; fi' "$SCRIPT" >/dev/null || {
    echo "FAIL: aggregated startup failure does not exit non-zero" >&2
    exit 1
}

if grep -F 'tailscale up failed' "$SCRIPT" | grep -F 'WARNING:' >/dev/null; then
    echo "FAIL: tailscale up failure is still warning-only" >&2
    exit 1
fi

echo "PASS: services-start propagates Tailscale policy application failures"
