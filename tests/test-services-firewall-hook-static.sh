#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
SCRIPT="$REPO_DIR/router/scripts/services-start"

[ -r "$SCRIPT" ] || { echo "FAIL: missing services-start" >&2; exit 1; }

grep -F 'if [ -x /jffs/scripts/firewall-start ]; then' "$SCRIPT" >/dev/null || {
    echo "FAIL: services-start does not explicitly check the managed firewall hook" >&2
    exit 1
}
grep -F '/jffs/scripts/firewall-start || { log "ERROR: firewall policy failed"; startup_failed=1; }' "$SCRIPT" >/dev/null || {
    echo "FAIL: firewall execution failure is not fatal" >&2
    exit 1
}
grep -F 'log "ERROR: required managed firewall hook is missing or not executable: /jffs/scripts/firewall-start"' "$SCRIPT" >/dev/null || {
    echo "FAIL: missing managed firewall hook is not logged as ERROR" >&2
    exit 1
}

hook_error_line="$(grep -n -F 'required managed firewall hook is missing or not executable' "$SCRIPT" | cut -d: -f1)"
hook_failure_line="$(awk -v start="$hook_error_line" 'NR > start && /startup_failed=1/ { print NR; exit }' "$SCRIPT")"
[ -n "$hook_error_line" ] && [ -n "$hook_failure_line" ] || {
    echo "FAIL: missing managed firewall hook does not set startup_failed" >&2
    exit 1
}
[ "$hook_failure_line" -le $((hook_error_line + 2)) ] || {
    echo "FAIL: missing managed firewall hook is not immediately aggregated as a startup failure" >&2
    exit 1
}

grep -F 'if [ "$startup_failed" -ne 0 ]; then log "ERROR: required service startup failed"; exit 1; fi' "$SCRIPT" >/dev/null || {
    echo "FAIL: aggregated startup failure does not exit non-zero" >&2
    exit 1
}

echo "PASS: services-start fails closed when the managed firewall hook is unavailable"
