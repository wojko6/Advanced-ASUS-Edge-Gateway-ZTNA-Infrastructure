#!/bin/sh

set -u

ROUTER_MANAGEMENT_IP="${1:-}"
DENIED_LAN_IP="${2:-}"

[ -n "$ROUTER_MANAGEMENT_IP" ] || {
    echo "Usage: $0 ROUTER_MANAGEMENT_IP [DENIED_LAN_IP]" >&2
    exit 2
}

FAILURES=0
SKIPPED=0
pass() { echo "PASS: $*"; }
fail() { echo "FAIL: $*"; FAILURES=$((FAILURES + 1)); }
skip() { echo "SKIP: $*"; SKIPPED=$((SKIPPED + 1)); }

if command -v dig >/dev/null 2>&1 && dig +time=3 +tries=1 @1.1.1.1 example.com A >/dev/null 2>&1; then
    pass "classic DNS query completed; confirm DNAT with router capture"
else
    fail "classic DNS query failed"
fi

# Historical tailnet-client policy probe: 8443 should be reachable and 22
# denied. These are not the current 5 GHz LAN WebUI/SSH management ports.
if command -v nc >/dev/null 2>&1; then
    if nc -z -w 3 "$ROUTER_MANAGEMENT_IP" 8443 >/dev/null 2>&1; then
        pass "router HTTPS reachable for this admin device"
    else
        fail "router HTTPS unavailable"
    fi
    if nc -z -w 3 "$ROUTER_MANAGEMENT_IP" 22 >/dev/null 2>&1; then
        fail "router SSH unexpectedly reachable"
    else
        pass "router SSH denied"
    fi
    if [ -n "$DENIED_LAN_IP" ]; then
        if nc -z -w 3 "$DENIED_LAN_IP" 445 >/dev/null 2>&1; then
            fail "SMB unexpectedly reachable"
        else
            pass "SMB denied"
        fi
    fi
else
    skip "router HTTPS port 8443 not checked: nc unavailable"
    skip "router SSH port 22 not checked: nc unavailable"
    if [ -n "$DENIED_LAN_IP" ]; then
        skip "LAN SMB port 445 not checked: nc unavailable"
    fi
fi

printf 'Summary: %s failure(s), %s skipped check(s)\n' "$FAILURES" "$SKIPPED"
[ "$FAILURES" -eq 0 ] || exit 1
[ "$SKIPPED" -eq 0 ] || exit 3
exit 0
