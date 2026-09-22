#!/bin/sh
set -eu

TEST_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH='' cd -- "$TEST_DIR/.." && pwd)"
SERVICES="$REPO_DIR/router/scripts/services-start"
HELPER="$REPO_DIR/router/scripts/tailscale-reconcile"

[ -r "$SERVICES" ] || { echo "FAIL: missing services-start" >&2; exit 1; }
[ -r "$HELPER" ] || { echo "FAIL: missing canonical Tailscale helper" >&2; exit 1; }

grep -F '"$EDGE_TAILSCALE_HELPER" ensure' "$SERVICES" >/dev/null || {
    echo "FAIL: services-start bypasses canonical Tailscale reconciliation" >&2
    exit 1
}
grep -F 'log "ERROR: Tailscale reconciliation failed"' "$SERVICES" >/dev/null || {
    echo "FAIL: services-start does not propagate reconciliation failure" >&2
    exit 1
}
grep -F 'startup_failed=1' "$SERVICES" >/dev/null || {
    echo "FAIL: services-start does not mark Tailscale reconciliation failure" >&2
    exit 1
}

for guard in \
    '--netfilter-mode="$EDGE_TS_NETFILTER_MODE"' \
    'tailscale --socket="$EDGE_TS_SOCKET" debug prefs' \
    'Tailscale netfilter mode verification failed' \
    'tailscale --socket="$EDGE_TS_SOCKET" status' \
    'failed to apply or verify Tailscale policy'
do
    grep -F -- "$guard" "$HELPER" >/dev/null || {
        echo "FAIL: canonical Tailscale policy guard missing: $guard" >&2
        exit 1
    }
done

grep -F '[ "$tailscale_netfilter_mode" = "0" ]' "$HELPER" >/dev/null || {
    echo "FAIL: canonical helper does not verify netfilter-mode=off" >&2
    exit 1
}

echo "PASS: services-start delegates to canonical Tailscale policy reconciliation"
