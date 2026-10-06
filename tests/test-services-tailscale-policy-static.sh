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


grep -F ': "${EDGE_TS_AUTO_UPDATE:=false}"' "$SCRIPT" >/dev/null || {
    echo "FAIL: Tailscale auto-update default is not disabled" >&2
    exit 1
}

grep -F '[ "$EDGE_TS_AUTO_UPDATE" = "false" ] || {' "$SCRIPT" >/dev/null || {
    echo "FAIL: Tailscale auto-update configuration is not fail-closed" >&2
    exit 1
}

grep -F 'tailscale --socket="$EDGE_TS_SOCKET" set --auto-update="$EDGE_TS_AUTO_UPDATE"' "$SCRIPT" >/dev/null || {
    echo "FAIL: services-start does not enforce Tailscale auto-update policy" >&2
    exit 1
}

grep -F 'ERROR: tailscale auto-update policy failed' "$SCRIPT" >/dev/null || {
    echo "FAIL: auto-update policy failure is not treated as an error" >&2
    exit 1
}


grep -F ': "${EDGE_FORCE_TAILSCALE_RESTART:=0}"' "$SCRIPT" >/dev/null || {
    echo "FAIL: maintenance restart is not disabled by default" >&2
    exit 1
}

grep -F 'stop_tailscaled_for_maintenance_restart()' "$SCRIPT" >/dev/null || {
    echo "FAIL: controlled Tailscale maintenance restart helper missing" >&2
    exit 1
}

grep -F '[ "$EDGE_FORCE_TAILSCALE_RESTART" = "1" ]' "$SCRIPT" >/dev/null || {
    echo "FAIL: services-start does not gate forced Tailscale restart" >&2
    exit 1
}

echo "PASS: services-start propagates Tailscale policy application failures"
